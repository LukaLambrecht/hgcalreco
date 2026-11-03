/*
Flatten a reco object to truth Branch association map (or the reverse map)
into simple vectors that can be read with FWLite. This is intended for the
"<collection>RecoToTruth<WorkingPoint>" and "<collection>TruthToReco" maps
produced by the truth graph associators in SimGeneral/TruthGraphAssociatorProducers.
In these maps, truth Branches are indexed by the particle id of their root
in the truth::Graph (not by an index in a truth collection).
Note: in the TruthToReco maps, the "SharedEnergy" output holds the shared energy
fraction normalized to the truth Branch (not the shared energy itself),
and the "Score" output holds the truth-normalized score.
*/

#include <memory>
#include <string>
#include <vector>

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

#include "SimDataFormats/Associations/interface/TICLAssociationMap.h"

class FlattenTruthBranchAssociator : public edm::global::EDProducer<> {
public:
  typedef ticl::TICLAssociationMap<ticl::mapWithSharedEnergyAndScore> AssocMap;

  explicit FlattenTruthBranchAssociator(edm::ParameterSet const& cfg) {
    token_ = consumes<AssocMap>(cfg.getParameter<edm::InputTag>("src"));
    destName_ = cfg.getParameter<std::string>("dest");
    firstName_ = cfg.getParameter<std::string>("first");
    secondName_ = cfg.getParameter<std::string>("second");

    produces<std::vector<unsigned int>>(destName_ + firstName_ + "Idx");
    produces<std::vector<unsigned int>>(destName_ + secondName_ + "Idx");
    produces<std::vector<float>>(destName_ + "SharedEnergy");
    produces<std::vector<float>>(destName_ + "Score");
  }

  void produce(edm::StreamID, edm::Event& event, edm::EventSetup const&) const override {
    edm::Handle<AssocMap> map;
    event.getByToken(token_, map);

    auto firstIdx = std::make_unique<std::vector<unsigned int>>();
    auto secondIdx = std::make_unique<std::vector<unsigned int>>();
    auto sharedEnergy = std::make_unique<std::vector<float>>();
    auto score = std::make_unique<std::vector<float>>();

    unsigned int first = 0;
    for (auto const& matches : map->getMap()) {
      for (auto const& match : matches) {
        firstIdx->push_back(first);
        secondIdx->push_back(match.index());
        sharedEnergy->push_back(match.sharedEnergy());
        score->push_back(match.score());
      }
      ++first;
    }

    event.put(std::move(firstIdx), destName_ + firstName_ + "Idx");
    event.put(std::move(secondIdx), destName_ + secondName_ + "Idx");
    event.put(std::move(sharedEnergy), destName_ + "SharedEnergy");
    event.put(std::move(score), destName_ + "Score");
  }

private:
  edm::EDGetTokenT<AssocMap> token_;
  std::string destName_;
  std::string firstName_;
  std::string secondName_;
};

DEFINE_FWK_MODULE(FlattenTruthBranchAssociator);
