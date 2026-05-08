#include <iostream>
#include <vector>

#include "FWCore/Framework/interface/one/EDAnalyzer.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/Frameworkfwd.h"

#include "DataFormats/Common/interface/Handle.h"
#include "FWCore/Utilities/interface/InputTag.h"

#include "SimDataFormats/CaloAnalysis/interface/CaloParticle.h"
#include "SimDataFormats/CaloAnalysis/interface/SimCluster.h"
#include "DataFormats/CaloRecHit/interface/CaloCluster.h"

#include "DataFormats/Common/interface/AssociationMap.h"
#include "DataFormats/Common/interface/OneToManyWithQualityGeneric.h"


// HGCalAssocTestAnalyzer class definition
class HGCalAssocTestAnalyzer : public edm::one::EDAnalyzer<> {
public:
  explicit HGCalAssocTestAnalyzer(const edm::ParameterSet&);
  void analyze(const edm::Event&, const edm::EventSetup&) override;

private:
  // define tokens (including correct data type)
  // for the objects/collections needed in this analyzer
  edm::EDGetTokenT<std::vector<CaloParticle>> cpToken_;
  edm::EDGetTokenT<std::vector<reco::CaloCluster>> lcToken_;
  edm::EDGetTokenT<
    edm::AssociationMap<
      edm::OneToManyWithQualityGeneric<
        std::vector<reco::CaloCluster>,
        std::vector<CaloParticle>,
        float,
        unsigned int
      >
    >
  > lctoCPToken_;
};


// Initializer
HGCalAssocTestAnalyzer::HGCalAssocTestAnalyzer(const edm::ParameterSet& iConfig)
{

  // instantiate the tokens using the correct input tags
  cpToken_ = consumes<std::vector<CaloParticle>>(
      edm::InputTag("mix", "MergedCaloTruth", "HLT"));
  lcToken_ = consumes<std::vector<reco::CaloCluster>>(
      edm::InputTag("hgcalMergeLayerClusters", "", "RECO"));
  lctoCPToken_ = consumes<
    edm::AssociationMap<
      edm::OneToManyWithQualityGeneric<
        std::vector<reco::CaloCluster>,
        std::vector<CaloParticle>,
        float,
        unsigned int
      >
    >
  >(edm::InputTag("layerClusterCaloParticleAssociation", "", "RECO"));
}


// Main per-event analyzer function
void HGCalAssocTestAnalyzer::analyze(const edm::Event& event,
                                    const edm::EventSetup&)
{

  // initialize handles
  edm::Handle<std::vector<CaloParticle>> cps;
  edm::Handle<std::vector<reco::CaloCluster>> lcs;
  edm::Handle<
    edm::AssociationMap<
      edm::OneToManyWithQualityGeneric<
        std::vector<reco::CaloCluster>,
        std::vector<CaloParticle>,
        float,
        unsigned int
      >
    >
  > map;

  // get objects/collections into handles
  event.getByToken(cpToken_, cps);
  event.getByToken(lcToken_, lcs);
  event.getByToken(lctoCPToken_, map);

  // basic printouts
  std::cout << "\n================ EVENT ================\n";
  std::cout << "CPs: " << cps->size()
            << "  LCs: " << lcs->size()
            << "  Map entries: " << map->size()
            << std::endl;

  // loop over map entries
  for (auto const& entry : *map) {

    // get LayerCluster
    auto const& lcRef = entry.key;
    auto const* lc = lcRef.get();
    auto lcidx = lcRef.key();

    if (!lc){
        std::cout << "WARNING: could not get LayerCluster" << std::endl;
        continue;
    }

    /*std::cout << "\nLC idx=" << lcRef.key()
              << " eta=" << lc->eta()
              << " energy=" << lc->energy()
              << std::endl;*/

    // loop over matching CaloParticles
    auto const& matches = entry.val;
    for (auto const& m : matches) {

      // get CaloParticle
      auto const& cpRef = m.first;
      float score = m.second;
      auto const* cp = cpRef.get();
      auto cpidx = cpRef.key();

      if (!cp){
        std::cout << "WARNING: could not get CaloParticle" << std::endl;    
        continue;
      }

      /*std::cout << "  -> CP idx=" << cpRef.key()
                << " eta=" << cp->eta()
                << " energy=" << cp->energy()
                << " score=" << score
                << std::endl;*/

      // check eta matching via direct reference access
      if (lc->eta() * cp->eta() < 0)
        std::cout << "  <<< DIRECT REF ETA SIGN MISMATCH >>>" << std::endl;
      
      // check eta matching via index to collections
      float lcidx_eta = (*lcs).at(lcidx).eta();
      float cpidx_eta = (*cps).at(cpidx).eta();
      if( lcidx_eta * cpidx_eta < 0 )
        std::cout << "  <<< IDX ETA SIGN MISMATCH >>>" << std::endl;
    }
  }
}

DEFINE_FWK_MODULE(HGCalAssocTestAnalyzer);
