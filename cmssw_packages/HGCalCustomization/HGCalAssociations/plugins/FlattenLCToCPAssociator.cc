/*
Flatten a LayerCluster to CaloParticle association map
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


class FlattenLCToCPAssociator :
  public edm::global::EDProducer<> {

public:

  typedef edm::AssociationMap<
    edm::OneToManyWithQualityGeneric<
      std::vector<reco::CaloCluster>,
      std::vector<CaloParticle>,
      float,
      unsigned int
    >
  > AssocMap;

  // constructor
  explicit FlattenLCToCPAssociator(edm::ParameterSet const& cfg)
  {
    token_ = consumes<AssocMap>(cfg.getParameter<edm::InputTag>("src"));
    destName_ = cfg.getParameter<std::string>("dest");
    produces<std::vector<unsigned int>>(destName_ + "LCIdx");
    produces<std::vector<unsigned int>>(destName_ + "CPIdx");
    produces<std::vector<float>>(destName_ + "Score");
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
    auto lcIdx = std::make_unique<std::vector<unsigned int>>();
    auto cpIdx = std::make_unique<std::vector<unsigned int>>();
    auto score = std::make_unique<std::vector<float>>();

    // loop over layerclusters
    for (auto const& entry : *map) {
      unsigned int lc = entry.key.key();

      // loop over caloparticles
      for (auto const& match : entry.val) {
        unsigned int cp = match.first.key();

        // add to vectors
        lcIdx->push_back(lc);
        cpIdx->push_back(cp);
        score->push_back(match.second);
      }
    }

    // add flat collections to the event
    event.put(std::move(lcIdx), destName_ + "LCIdx");
    event.put(std::move(cpIdx), destName_ + "CPIdx");
    event.put(std::move(score), destName_ + "Score");
  }

private:

  edm::EDGetTokenT<AssocMap> token_;
  std::string destName_;
};

DEFINE_FWK_MODULE(FlattenLCToCPAssociator);
