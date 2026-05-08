#include <iostream>
#include <memory>
#include <vector>
#include <string>

#include "FWCore/FWLite/interface/FWLiteEnabler.h"
#include "DataFormats/FWLite/interface/Event.h"
#include "DataFormats/FWLite/interface/Handle.h"

#include "FWCore/FWLite/interface/FWLiteEnabler.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"

#include "SimDataFormats/CaloAnalysis/interface/CaloParticle.h"
#include "SimDataFormats/CaloAnalysis/interface/SimCluster.h"

#include "DataFormats/Common/interface/AssociationMap.h"
#include "DataFormats/Common/interface/OneToManyWithQualityGeneric.h"
#include "DataFormats/Common/interface/Ref.h"

#include "DataFormats/CaloRecHit/interface/CaloCluster.h"

#include "TFile.h"

typedef edm::AssociationMap<
    edm::OneToManyWithQualityGeneric<
        std::vector<CaloParticle>,
        std::vector<reco::CaloCluster>,
        std::pair<float,float>,
        unsigned int,
        edm::RefProd<std::vector<CaloParticle> >,
        edm::RefProd<std::vector<reco::CaloCluster> >,
        edm::Ref<
            std::vector<CaloParticle>,
            CaloParticle,
            edm::refhelper::FindUsingAdvance<std::vector<CaloParticle>,CaloParticle>
        >,
        edm::Ref<
            std::vector<reco::CaloCluster>,
            reco::CaloCluster,
            edm::refhelper::FindUsingAdvance<std::vector<reco::CaloCluster>,reco::CaloCluster> 
        >
    >
> CPToLCMap;

typedef edm::AssociationMap<
    edm::OneToManyWithQualityGeneric<
        std::vector<reco::CaloCluster>,
        std::vector<CaloParticle>,
        float,
        unsigned int,
        edm::RefProd<std::vector<reco::CaloCluster> >,
        edm::RefProd<std::vector<CaloParticle> >,
        edm::Ref<
            std::vector<reco::CaloCluster>,
            reco::CaloCluster,
            edm::refhelper::FindUsingAdvance<std::vector<reco::CaloCluster>,reco::CaloCluster>
        >,
        edm::Ref<
            std::vector<CaloParticle>,
            CaloParticle,edm::refhelper::FindUsingAdvance<std::vector<CaloParticle>,CaloParticle>
        > 
    > 
> LCToCPMap;


int main(int argc, char* argv[]) {

    FWLiteEnabler::enable();

    if (argc < 2) {
        std::cout << "Usage: testHGCalAssociations file.root [file2.root ...]" << std::endl;
        return 1;
    }

    for (int ifile = 1; ifile < argc; ++ifile) {

        std::string filename(argv[ifile]);

        std::cout << "Reading file: " << filename << std::endl;

        TFile file(filename.c_str());

        fwlite::Event ev(&file);

        int ievt = 0;

        for (ev.toBegin(); !ev.atEnd(); ++ev, ++ievt) {

            std::cout << "\n========================================" << std::endl;
            std::cout << "Event " << ievt << std::endl;
            std::cout << "========================================" << std::endl;

            //
            // HANDLES
            //

            fwlite::Handle<std::vector<CaloParticle>> h_caloParticles;
            h_caloParticles.getByLabel(
                ev,
                "mix",
                "MergedCaloTruth",
                "HLT"
            );

            fwlite::Handle<std::vector<reco::CaloCluster>> h_layerClusters;
            h_layerClusters.getByLabel(
                ev,
                "hgcalMergeLayerClusters",
                "",
                "RECO"
            );

            fwlite::Handle<LCToCPMap> h_lctocp;
            h_lctocp.getByLabel(
                ev,
                "layerClusterCaloParticleAssociation",
                "",
                "RECO"
            );

            fwlite::Handle<CPToLCMap> h_cptolc;
            h_cptolc.getByLabel(
                ev,
                "layerClusterCaloParticleAssociation",
                "",
                "RECO"
            );

            if (!h_caloParticles.isValid()) {
                std::cout << "CaloParticle handle invalid" << std::endl;
                continue;
            }

            if (!h_layerClusters.isValid()) {
                std::cout << "LayerCluster handle invalid" << std::endl;
                continue;
            }

            if (!h_lctocp.isValid()) {
                std::cout << "LC->CP map invalid" << std::endl;
                continue;
            }

            if (!h_cptolc.isValid()) {
                std::cout << "CP->LC map invalid" << std::endl;
                continue;
            }

            auto const& caloParticles = *h_caloParticles;
            auto const& layerClusters = *h_layerClusters;

            auto const& lctocp = *h_lctocp;
            auto const& cptolc = *h_cptolc;

            //
            // SIZES
            //

            std::cout << "--- Sizes ---" << std::endl;

            std::cout << "CP collection size      = "
                      << caloParticles.size() << std::endl;

            std::cout << "LC collection size      = "
                      << layerClusters.size() << std::endl;

            std::cout << "LC->CP map size         = "
                      << lctocp.size() << std::endl;

            std::cout << "CP->LC map size         = "
                      << cptolc.size() << std::endl;

            //
            // LOOP OVER LC -> CP
            //

            std::cout << "\n--- LC -> CP ---" << std::endl;

            for (auto it = lctocp.begin(); it != lctocp.end(); ++it) {

                auto const& lcRef = it->key;
                unsigned int lcidx = lcRef.key();
                auto const* lc = lcRef.get();

                //auto const& values = lctocp[lcRef];
                auto const& values = it->val;

                for (auto const& val : values) {

                    auto const& cpRef = val.first;
                    float score = val.second;
                    unsigned int cpidx = cpRef.key();
                    auto const* cp = cpRef.get();

                    //
                    // CHECK ETA SIGN WITH DIRECT REFERENCES
                    //

                    if (lc && cp) {

                        if (lc->eta() * cp->eta() < 0.f) {

                            std::cout << "<<< DIRECT REF ETA SIGN MISMATCH >>>" << std::endl;
                            
                            std::cout << "LC idx = " << lcidx;
                            std::cout << "  eta = " << lc->eta()
                                << "  energy = " << lc->energy();
                            std::cout << std::endl;

                            std::cout << "    -> CP idx = " << cpidx;
                            std::cout << "  eta = "
                                  << cp->eta()
                                  << "  energy = "
                                  << cp->energy();
                            std::cout << "  score = " << score;
                            std::cout << std::endl;
                        }
                    }

                    //
                    // Check eta sign with collection access
                    //
                    float lcidx_eta = layerClusters.at(lcidx).eta();
                    float cpidx_eta = caloParticles.at(cpidx).eta();
                    if (lcidx_eta * cpidx_eta < 0.f) {

                            std::cout << "<<< INDEX ETA SIGN MISMATCH >>>" << std::endl;

                            std::cout << "LC idx = " << lcidx;
                            std::cout << "  eta = " << lcidx_eta;
                            std::cout << std::endl;

                            std::cout << "    -> CP idx = " << cpidx;
                            std::cout << "  eta = " << cpidx_eta;
                            std::cout << "  score = " << score;
                            std::cout << std::endl;
                    }

                    //
                    // CHECK DIRECT COLLECTION ACCESS
                    //

                    if (lcidx < layerClusters.size()) {

                        auto const& lc2 = layerClusters.at(lcidx);
                        float eta2 = lc2.eta();
                        if (lc && std::abs(eta2 - lc->eta()) > 1e-6) {
                            std::cout
                                << "<<< COLLECTION MISMATCH >>>"
                                << " lc.get eta = "
                                << lc->eta()
                                << " collection eta = "
                                << eta2
                                << std::endl;
                        }
                    }
                }
            }

            if(ievt >= 2) break;
            continue; // temp for going step by step

            //
            // LOOP OVER CP -> LC
            //

            std::cout << "\n--- CP -> LC ---" << std::endl;

            for (auto it = cptolc.begin(); it != cptolc.end(); ++it) {

                auto const& cpRef = it->key;

                unsigned int cpidx = cpRef.key();

                auto const* cp = cpRef.get();

                std::cout << "\nCP idx = " << cpidx;

                if (cp) {
                    std::cout << "  eta = "
                              << cp->eta()
                              << "  energy = "
                              << cp->energy();
                }

                std::cout << std::endl;

                auto const& values = cptolc[cpRef];

                for (auto const& val : values) {

                    auto const& lcRef = val.first;

                    auto const& quality = val.second;

                    unsigned int lcidx = lcRef.key();

                    auto const* lc = lcRef.get();

                    std::cout
                        << "    -> LC idx = "
                        << lcidx;

                    if (lc) {
                        std::cout
                            << "  eta = "
                            << lc->eta()
                            << "  energy = "
                            << lc->energy();
                    }

                    std::cout
                        << "  score1 = "
                        << quality.first
                        << "  score2 = "
                        << quality.second;

                    if (lc && cp) {

                        if (lc->eta() * cp->eta() < 0.f) {

                            std::cout
                                << "   <<< ETA SIGN MISMATCH >>>";
                        }
                    }

                    std::cout << std::endl;
                }
            }
        }
    }

    return 0;
}
