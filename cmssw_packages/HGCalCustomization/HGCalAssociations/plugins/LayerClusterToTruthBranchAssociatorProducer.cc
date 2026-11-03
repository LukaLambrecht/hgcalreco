/*
Associate LayerClusters to truth Branches of the MC-truth graph.
This is not available upstream (SimGeneral/TruthGraphAssociatorProducers only provides
tracks, tracksters, PF clusters and vertices), but it follows exactly the same logic
as the trackster domain of AllRecoToTruthBranchAssociatorsProducer there,
only with a LayerCluster instead of a Trackster as reco object:
- the reco hits of a LayerCluster are its (DetId, fraction) pairs,
  as given by truth::recoHits(reco::CaloCluster const&) in PhysicsTools/TruthInfo;
- the shared energy metric weights each cell by its rechit energy;
- one reco-to-truth map is produced per working point ("<key>RecoToTruth<WorkingPoint>"),
  and one truth-to-reco map ("<key>TruthToReco"), in the same format as upstream,
  so they can be flattened with FlattenTruthBranchAssociator.
In these maps, truth Branches are indexed by the particle id of their root in the truth::Graph.
*/

#include <memory>
#include <optional>
#include <span>
#include <string>
#include <vector>

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/Exception.h"

#include "DataFormats/CaloRecHit/interface/CaloCluster.h"
#include "DataFormats/DetId/interface/DetId.h"
#include "DataFormats/HGCRecHit/interface/HGCRecHitCollections.h"
#include "SimDataFormats/Associations/interface/TICLAssociationMap.h"
#include "SimDataFormats/TruthInfo/interface/Graph.h"
#include "SimDataFormats/TruthInfo/interface/LogicalGraphHitIndex.h"
#include "PhysicsTools/TruthInfo/interface/Branch.h"
#include "PhysicsTools/TruthInfo/interface/BranchHitAssociator.h"
#include "PhysicsTools/TruthInfo/interface/RecoHitAdapters.h"

class LayerClusterToTruthBranchAssociatorProducer : public edm::global::EDProducer<> {
public:
  typedef ticl::TICLAssociationMap<ticl::mapWithSharedEnergyAndScore> AssocMap;

  explicit LayerClusterToTruthBranchAssociatorProducer(edm::ParameterSet const& cfg) {
    graphToken_ = consumes<truth::Graph>(cfg.getParameter<edm::InputTag>("src"));
    hitIndexToken_ = consumes<truth::LogicalGraphHitIndex>(cfg.getParameter<edm::InputTag>("hitIndex"));
    layerClustersToken_ = consumes<std::vector<reco::CaloCluster>>(cfg.getParameter<edm::InputTag>("layerClusters"));
    for (auto const& tag : cfg.getParameter<std::vector<edm::InputTag>>("hgcalRecHits"))
      hgcalRecHitTokens_.push_back(consumes<HGCRecHitCollection>(tag));
    targetsToken_ = consumes<std::vector<unsigned int>>(cfg.getParameter<edm::InputTag>("targetsSrc"));
    assignableTargetsToken_ = consumes<std::vector<unsigned int>>(cfg.getParameter<edm::InputTag>("assignableTargetsSrc"));
    key_ = cfg.getParameter<std::string>("key");

    // detectors of the shared energy fraction denominator
    // (only the HGCAL ones are supported, since this is only meant for HGCAL LayerClusters)
    denominatorDetectors_ = 0u;
    for (auto const& name : cfg.getParameter<std::vector<std::string>>("denominatorDetectors")) {
      DetId::Detector det;
      if (name == "HGCalEE")
        det = DetId::HGCalEE;
      else if (name == "HGCalHSi")
        det = DetId::HGCalHSi;
      else if (name == "HGCalHSc")
        det = DetId::HGCalHSc;
      else
        throw cms::Exception("Configuration") << "unsupported entry '" << name << "' in denominatorDetectors";
      denominatorDetectors_ |= 1u << static_cast<uint32_t>(det);
    }
    if (denominatorDetectors_ == 0u)
      denominatorDetectors_ = truth::BranchHitAssociator::kAllDetectors;

    // working points ("Fixed" is the plain per-root match, all others are adaptive)
    workingPointNames_ = cfg.getParameter<std::vector<std::string>>("workingPointNames");
    adaptiveReverseWeight_ = cfg.getParameter<std::vector<double>>("adaptiveReverseWeight");
    adaptiveMaxReverseScore_ = cfg.getParameter<std::vector<double>>("adaptiveMaxReverseScore");
    if (workingPointNames_.size() != adaptiveReverseWeight_.size() ||
        workingPointNames_.size() != adaptiveMaxReverseScore_.size()) {
      throw cms::Exception("Configuration")
          << "workingPointNames, adaptiveReverseWeight and adaptiveMaxReverseScore must have the same length";
    }

    for (auto const& name : workingPointNames_)
      produces<AssocMap>(key_ + "RecoToTruth" + name);
    produces<AssocMap>(key_ + "TruthToReco");
  }

  void produce(edm::StreamID, edm::Event& event, edm::EventSetup const&) const override {
    auto const& graph = event.get(graphToken_);
    auto const& hitIndex = event.get(hitIndexToken_);
    auto const& layerClusters = event.get(layerClustersToken_);
    auto const& selectedRoots = event.get(targetsToken_);
    const unsigned int nBranches = graph.nParticles();
    const unsigned int nReco = layerClusters.size();

    // rechit energy per cell, used as weight in the shared energy metric
    truth::CellEnergyTable recHitEnergies;
    for (auto const& token : hgcalRecHitTokens_) {
      auto const& hits = event.get(token);
      recHitEnergies.reserve(recHitEnergies.size() + hits.size());
      for (auto const& hit : hits)
        recHitEnergies.add(hit.id().rawId(), hit.energy());
    }
    recHitEnergies.finalize();

    // mask of the truth Branches a reco object may be assigned to (adaptive working points)
    std::vector<uint8_t> isAssignable(nBranches, 0);
    for (const unsigned int id : event.get(assignableTargetsToken_)) {
      if (id < nBranches)
        isAssignable[id] = 1;
    }

    // make output maps
    std::vector<std::unique_ptr<AssocMap>> recoToTruthPerWp;
    for (std::size_t wp = 0; wp < workingPointNames_.size(); ++wp)
      recoToTruthPerWp.push_back(std::make_unique<AssocMap>(nReco));
    auto truthToReco = std::make_unique<AssocMap>(nBranches);

    if (nReco > 0) {
      // orders a particle before an ancestor that owns the same cells
      const std::vector<uint32_t> generations = truth::particleGenerations(graph);
      const truth::BranchHitAssociator associator(hitIndex,
                                                  selectedRoots,
                                                  truth::BranchHitAssociator::Metric::SharedEnergy,
                                                  truth::HitChannel::Calo,
                                                  /*emptyRootsMeansAll=*/false,
                                                  denominatorDetectors_,
                                                  &recHitEnergies,
                                                  generations);

      std::vector<truth::BranchMatch> assignableMatches;
      std::vector<truth::BranchMatch> fixedRow;
      for (unsigned int i = 0; i < nReco; ++i) {
        const auto recoHits = truth::recoHits(layerClusters[i]);
        if (recoHits.empty())
          continue;
        const auto matches = associator.bestBranches(std::span<const truth::RecoHit>(recoHits));

        // assignable roots first (in order of ascending score), then the other ones
        assignableMatches.clear();
        for (auto const& match : matches) {
          if (match.rootParticleId < nBranches && isAssignable[match.rootParticleId] != 0)
            assignableMatches.push_back(match);
        }
        fixedRow = assignableMatches;
        for (auto const& match : matches) {
          if (match.rootParticleId >= nBranches || isAssignable[match.rootParticleId] == 0)
            fixedRow.push_back(match);
        }

        // reco to truth (reco-normalized score), per working point
        for (std::size_t wp = 0; wp < workingPointNames_.size(); ++wp) {
          if (workingPointNames_[wp] != "Fixed") {
            const auto match = truth::BranchHitAssociator::bestAdaptiveBranch(
                std::span<const truth::BranchMatch>(assignableMatches),
                adaptiveReverseWeight_[wp],
                adaptiveMaxReverseScore_[wp]);
            if (match.rootParticleId != truth::BranchMatch::kInvalidRoot)
              recoToTruthPerWp[wp]->insert(i, match.rootParticleId, match.sharedEnergy, match.score);
          } else {
            for (auto const& match : fixedRow)
              recoToTruthPerWp[wp]->insert(i, match.rootParticleId, match.sharedEnergy, match.score);
          }
        }

        // truth to reco (truth-normalized shared energy fraction and score)
        for (auto const& match : matches) {
          if (match.rootParticleId >= nBranches) {
            throw cms::Exception("Configuration")
                << "the hit index and the truth graph disagree on the particle count."
                << " Both products must come from the same event.";
          }
          truthToReco->insert(match.rootParticleId, i, match.sharedEnergyFraction, match.reverseScore);
        }
      }
    }

    for (std::size_t wp = 0; wp < workingPointNames_.size(); ++wp)
      event.put(std::move(recoToTruthPerWp[wp]), key_ + "RecoToTruth" + workingPointNames_[wp]);
    truthToReco->sort(truth::byAscendingScore);
    event.put(std::move(truthToReco), key_ + "TruthToReco");
  }

private:
  edm::EDGetTokenT<truth::Graph> graphToken_;
  edm::EDGetTokenT<truth::LogicalGraphHitIndex> hitIndexToken_;
  edm::EDGetTokenT<std::vector<reco::CaloCluster>> layerClustersToken_;
  std::vector<edm::EDGetTokenT<HGCRecHitCollection>> hgcalRecHitTokens_;
  edm::EDGetTokenT<std::vector<unsigned int>> targetsToken_;
  edm::EDGetTokenT<std::vector<unsigned int>> assignableTargetsToken_;
  std::string key_;
  uint32_t denominatorDetectors_;
  std::vector<std::string> workingPointNames_;
  std::vector<double> adaptiveReverseWeight_;
  std::vector<double> adaptiveMaxReverseScore_;
};

DEFINE_FWK_MODULE(LayerClusterToTruthBranchAssociatorProducer);
