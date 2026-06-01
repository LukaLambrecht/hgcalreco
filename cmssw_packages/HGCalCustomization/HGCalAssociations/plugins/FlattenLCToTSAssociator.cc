/*
Flatten a LayerCluster to Trackster association map into simple vectors
that can be read with FWLite.
*/

#include <memory>
#include <string>
#include <vector>

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

#include "DataFormats/CaloRecHit/interface/CaloCluster.h"
#include "DataFormats/HGCalReco/interface/Trackster.h"
#include "SimDataFormats/Associations/interface/TICLAssociationMap.h"

class FlattenLCToTSAssociator : public edm::global::EDProducer<> {
public:
  typedef ticl::AssociationMap<ticl::mapWithSharedEnergy, std::vector<reco::CaloCluster>, std::vector<ticl::Trackster>>
      AssocMap;

  explicit FlattenLCToTSAssociator(edm::ParameterSet const& cfg) {
    token_ = consumes<AssocMap>(cfg.getParameter<edm::InputTag>("src"));
    destName_ = cfg.getParameter<std::string>("dest");
    secondName_ = cfg.getParameter<std::string>("second");

    produces<std::vector<unsigned int>>(destName_ + "LCIdx");
    produces<std::vector<unsigned int>>(destName_ + secondName_ + "Idx");
    produces<std::vector<float>>(destName_ + "SharedEnergy");
  }

  void produce(edm::StreamID, edm::Event& event, edm::EventSetup const&) const override {
    edm::Handle<AssocMap> map;
    event.getByToken(token_, map);

    auto lcIdx = std::make_unique<std::vector<unsigned int>>();
    auto tsIdx = std::make_unique<std::vector<unsigned int>>();
    auto sharedEnergy = std::make_unique<std::vector<float>>();

    unsigned int lc = 0;
    for (auto const& matches : map->getMap()) {
      for (auto const& match : matches) {
        lcIdx->push_back(lc);
        tsIdx->push_back(match.index());
        sharedEnergy->push_back(match.sharedEnergy());
      }
      ++lc;
    }

    event.put(std::move(lcIdx), destName_ + "LCIdx");
    event.put(std::move(tsIdx), destName_ + secondName_ + "Idx");
    event.put(std::move(sharedEnergy), destName_ + "SharedEnergy");
  }

private:
  edm::EDGetTokenT<AssocMap> token_;
  std::string destName_;
  std::string secondName_;
};

DEFINE_FWK_MODULE(FlattenLCToTSAssociator);
