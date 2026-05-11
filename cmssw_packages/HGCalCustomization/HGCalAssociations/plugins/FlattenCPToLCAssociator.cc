/*
Flatten a CaloParticle to LayerCluster association map
into a simple structure that can be read with FWLite
*/


#include <memory>
#include <vector>

#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

#include "DataFormats/Common/interface/AssociationMap.h"
#include "DataFormats/Common/interface/OneToManyWithQualityGeneric.h"

#include "DataFormats/CaloRecHit/interface/CaloCluster.h"
#include "SimDataFormats/CaloAnalysis/interface/CaloParticle.h"


class FlattenCPToLCAssociator :
  public edm::global::EDProducer<> {

public:

  typedef edm::AssociationMap<
    edm::OneToManyWithQualityGeneric<
      std::vector<CaloParticle>,
      std::vector<reco::CaloCluster>,
      std::pair<float, float>,
      unsigned int
    >
  > AssocMap;

  // constructor
  explicit FlattenCPToLCAssociator(edm::ParameterSet const& cfg)
  {
    token_ = consumes<AssocMap>(cfg.getParameter<edm::InputTag>("src"));
    destName_ = cfg.getParameter<std::string>("dest");
    produces<std::vector<unsigned int>>(destName_ + "CPIdx");
    produces<std::vector<unsigned int>>(destName_ + "LCIdx");
    produces<std::vector<float>>(destName_ + "Score");
    produces<std::vector<float>>(destName_ + "SharedEnergyFraction");
  }

  // main 
  void produce(edm::StreamID,
               edm::Event& event,
               edm::EventSetup const&) const override
  {

    // get the association map
    edm::Handle<AssocMap> map;
    event.getByToken(token_, map);

    // initializations
    auto cpIdx = std::make_unique<std::vector<unsigned int>>();
    auto lcIdx = std::make_unique<std::vector<unsigned int>>();
    auto score = std::make_unique<std::vector<float>>();
    auto eFrac = std::make_unique<std::vector<float>>();

    // loop over caloparticles
    for (auto const& entry : *map) {
      unsigned int cp = entry.key.key();

      // loop over layerclusters
      for (auto const& match : entry.val) {
        unsigned int lc = match.first.key();

        // add to vectors
        cpIdx->push_back(cp);
        lcIdx->push_back(lc);
        score->push_back(match.second.first);
        eFrac->push_back(match.second.second);
      }
    }

    // add flat collections to the event
    event.put(std::move(cpIdx), destName_ + "CPIdx");
    event.put(std::move(lcIdx), destName_ + "LCIdx");
    event.put(std::move(score), destName_ + "Score");
    event.put(std::move(eFrac), destName_ + "SharedEnergyFraction");
  }

private:

  edm::EDGetTokenT<AssocMap> token_;
  std::string destName_;
};

DEFINE_FWK_MODULE(FlattenCPToLCAssociator);
