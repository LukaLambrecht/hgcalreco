# Run a sample production chain

import os
import sys
import json
import argparse

topdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(topdir)

import tools.condortools as ct


if __name__=='__main__':

    # read command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--fragment', required=True)
    parser.add_argument('-c', '--chain', required=True)
    parser.add_argument('-w', '--workdir', required=True)
    parser.add_argument('-n', '--events-per-job', default=10, type=int)
    parser.add_argument('-j', '--number-of-jobs', default=1, type=int)
    parser.add_argument('--tag', default=None)
    parser.add_argument('--cmssw', default=None)
    parser.add_argument('--proxy', default=None)
    parser.add_argument('--overwrite', default=False, action='store_true')
    parser.add_argument('--remove-intermediate-output', default=False, action='store_true')
    parser.add_argument('--output-mode', default='hgcal', choices=['hgcal', 'full'])
    parser.add_argument('--request-memory', default=2000, type=int,
        help='Requested memory in MB. Increase this for pileup chains,'
             ' which need substantially more memory than no-pileup ones'
             ' (e.g. 8000 for PU200).')
    args = parser.parse_args()

    # parse tag
    tagstr = '' if args.tag is None else f'_{args.tag}'

    # set CMSSW if provided
    # priority:
    # - command line arg
    # - environment
    cmssw = None
    envcmssw = os.getenv('CMSSW_BASE')
    if args.cmssw is not None:
        cmssw = os.path.abspath(args.cmssw)
        if not os.path.exists(cmssw):
            raise Exception(f'Provided CMSSW {cmssw} does not exist.')
        if envcmssw is not None and envcmssw!=cmssw:
            msg = 'WARNING: provided CMSSW {cmssw} is different from current environment CMSSW {envcmssw}.'
            print(msg)
    elif envcmssw is not None:
        cmssw = envcmssw
    else:
        msg = 'A CMSSW version must be provided either explicitly with --cmssw'
        msg += ' or implicitly in the environment.'
        raise Exception(msg)
    print(f'Found following CMSSW: {cmssw}')

    # check if the fragment exists and move it to Configuration/GenProduction
    if not os.path.exists(args.fragment):
        raise Exception(f'Fragment {fragment} does not exist.')
    cmd = f'cp {args.fragment} $CMSSW_BASE/src/Configuration/GenProduction/python/'
    print(f'Copying fragment: {cmd}')
    os.system(cmd)

    # read the chain
    cmds = []
    with open(args.chain, 'r') as f:
        chain = json.load(f)
    for step in chain:
        stepfile = os.path.join('cmsdriver/steps', step)
        with open(stepfile) as f:
            lines = f.readlines()
        cmd = ' '.join([line.strip(' \\\n\t') for line in lines])
        cmds.append(cmd)

    # replace placeholders
    for stepidx, cmd in enumerate(cmds):
        cmd = cmd.replace('FRAGMENT', os.path.basename(args.fragment))
        cmd = cmd.replace('FILEIN', f'step{stepidx-1}.root')
        cmd = cmd.replace('FILEOUT', f'step{stepidx}.root')
        cmd = cmd.replace('NUM_EVENTS', f'{args.events_per_job}')
        cmds[stepidx] = cmd

    # other customizations
    for stepidx, cmd in enumerate(cmds):

        # get customization options that are already in the command (if any)
        customization = []
        tag = 'customise_commands'
        if f'--{tag}' in cmd:
            parts = cmd.split('--')
            idx = [idx for idx, part in enumerate(parts) if part.startswith(tag)][0]
            customization = [parts[idx].replace(tag, '').strip(';" \t\n')]
            parts.pop(idx)
            cmd = '--'.join(parts)

        # set output of the last step
        # note: this currently assumes the last step is MiniAOD level,
        #       maybe later try to generalize.
        if stepidx == len(cmds)-1:

            # Produce association between TrackingParticles and RecoTracks.
            # These products do not depend on HGCAL CLUE settings,
            # but SimTrackstersProducer needs them later in the re-reco step in
            # order to build SimTracksters(:fromCPs);
            # hence these association maps are implicitly needed
            # for CaloParticle-to-Trackster or CaloParticle-to-TiclCandidate association scores.
            has_tracking_associations = any(
                'trackingParticleRecoTrackAsssociation' in item
                for item in customization
            )
            if not has_tracking_associations:
                customization.append("process.load('SimGeneral.TrackingAnalysis.simHitTPAssociation_cfi')")
                customization.append("process.load('SimTracker.TrackerHitAssociation.tpClusterProducer_cfi')")
                customization.append("process.load('SimTracker.TrackAssociatorProducers.quickTrackAssociatorByHits_cfi')")
                customization.append("process.load('SimTracker.TrackAssociation.trackingParticleRecoTrackAsssociation_cfi')")
                customization.append(
                    "process.trackingTruthAssociationTask = cms.Task("
                    "process.simHitTPAssocProducer, "
                    "process.tpClusterProducer, "
                    "process.quickTrackAssociatorByHits, "
                    "process.trackingParticleRecoTrackAsssociation)"
                )
                customization.append("process.reconstruction_step.associate(process.trackingTruthAssociationTask)")

            # output option 1: keep everything
            # note: gives very large files, but contains all info to re-run the reco step.
            # note: copied from examples, see README for more info.
            # note: does not actually seem to keep everything, some RECO products are dropped
            #       (but not sure which ones or why...)
            if args.output_mode == "full":
                customization.append('process.MINIAODSIMoutput.outputCommands.append(\'keep *_*_*_HLT\')')
                customization.append('process.MINIAODSIMoutput.outputCommands.append(\'keep *_*_*_SIM\')')
                # custom additions to be able to run the "minimal" (i.e. HGCAL-specific) re-reco on these files
                # note: without this addition, some RECO products (in particular the HGCalRecHits)
                #       seem to be missing from the produced files; not sure why because other RECO
                #       collections are present.
                customization.append('process.MINIAODSIMoutput.outputCommands.append(\'keep *_HGCalRecHit_*_*\')')
                customization.append('process.MINIAODSIMoutput.outputCommands.append(\'keep *_HGCalUncalibRecHit_*_*\')')
                customization.append('process.MINIAODSIMoutput.outputCommands.append(\'keep *_hgcalDigis_*_*\')')
                customization.append('process.MINIAODSIMoutput.outputCommands.append(\'keep *_hfnoseDigis_*_*\')')
                # tracking and timing inputs needed by TICL merge/PF-TICL
                # and by SimTrackster construction in the downstream re-reco.
                # Keep the explicit CMSSW RECO track products as well as the
                # broad labels: persisted TICL/MTD objects can carry refs back
                # to the original reco::Track collection.
                customization.append('process.MINIAODSIMoutput.outputCommands.append(\'keep *_generalTracks_*_*\')')
                customization.append('process.MINIAODSIMoutput.outputCommands.append(\'keep *_muons1stStep_*_*\')')
                customization.append('process.MINIAODSIMoutput.outputCommands.append(\'keep *_globalMuons_*_*\')')
                customization.append('process.MINIAODSIMoutput.outputCommands.append(\'keep *_standAloneMuons_*_*\')')
                customization.append('process.MINIAODSIMoutput.outputCommands.append(\'keep *_tevMuons_*_*\')')
                customization.append('process.MINIAODSIMoutput.outputCommands.append(\'keep *_trackExtenderWithMTD_*_*\')')
                customization.append('process.MINIAODSIMoutput.outputCommands.append(\'keep *_tofPID_*_*\')')
                customization.append('process.MINIAODSIMoutput.outputCommands.append(\'keep *_mtdTrackQualityMVA_*_*\')')
                customization.append('process.MINIAODSIMoutput.outputCommands.append(\'keep *_trackingParticleRecoTrackAsssociation_*_*\')')
                customization.append('process.MINIAODSIMoutput.outputCommands.append(\'keep *_simHitTPAssocProducer_simTrackToTP_*\')')

            # output option 2: hgcal-specific minimal content
            # note: gives lean files, but not sure if they contain enough info to re-run HGCAL reco on top.
            #       update: in fact they do, but only with the minimal/selective setup in run-hgcal-reco,
            #       does not contain all needed info for re-running the full reco!
            elif args.output_mode == "hgcal":

                drop = [
                '*_*_*_*'
                ]
                keep = [
                  # minimal inputs for rerunning HGCAL local reco from digis
                  '*_hgcalDigis_*_*',
                  '*_hfnoseDigis_*_*',
                  # central reco objects, so the production file can still be used
                  # directly by the analysis scripts as a reference reco sample
                  '*_HGCalRecHit_*_*',
                  '*_hgcalMergeLayerClusters_*_*',
                  '*_ticlTracksters*_*_*', # includes Tracksters and ticlCandidates in v4
                  '*_ticlTracksterLinks*_*_*', # linked Tracksters in v5
                  '*_ticlCandidate_*_*', # v5 ticlCandidates
                  '*_pfTICL_*_*',
                  # truth needed for LC and Trackster performance checks
                  '*_mix_MergedCaloTruth_*',
                  '*_mix_MergedTrackTruth_*',
                  '*_mix_MergedMtdTruthST_*',
                  '*_g4SimHits_HGCHitsEE_*',
                  '*_g4SimHits_HGCHitsHEfront_*',
                  '*_g4SimHits_HGCHitsHEback_*',
                  '*GenParticle*_*_*_*',
                  # tracking and timing inputs needed by TICL merge/PF-TICL
                  # and by SimTrackster construction
                  '*_generalTracks_*_*',
                  '*_muons1stStep_*_*',
                  '*_globalMuons_*_*',
                  '*_standAloneMuons_*_*',
                  '*_tevMuons_*_*',
                  '*_trackExtenderWithMTD_*_*',
                  '*_tofPID_*_*',
                  '*_mtdTrackQualityMVA_*_*',
                  '*_trackingParticleRecoTrackAsssociation_*_*',
                  '*_simHitTPAssocProducer_simTrackToTP_*',
                  # associations, if produced in the reconstruction chain
                  '*_layerClusterCaloParticleAssociation_*_*',
                  '*_layerClusterSimClusterAssociation_*_*',
                  '*_allTrackstersToSimTrackstersAssociations*_*_*',
                  '*_allLayerClusterToTracksterAssociations*_*_*'
                ]
                for collection in drop:
                    customization.append(f'process.MINIAODSIMoutput.outputCommands.append(\'drop {collection}\')')
                for collection in keep:
                    customization.append(f'process.MINIAODSIMoutput.outputCommands.append(\'keep {collection}\')')

            else:
                msg = f'Output mode "{args.output_mode}" not recognized.'
                raise Exception(msg)

        # others: to do as the need arises

        # (re-)add customization to command
        if len(customization)==0: continue
        customizationstr = '; '.join(customization)
        cmd += f' --{tag} "{customizationstr}"'

        # replace original command
        cmds[stepidx] = cmd

    # make set of commands for each job
    job_cmds = []
    for jobidx in range(args.number_of_jobs):
        this_job_cmds = []
        # add random seed
        # note: use jobidx + 1 because using random seed 0 gives errors!
        # note: the --customise_commands option seems to silently override any previous option with the same name...
        #       so need to take care in how to add it.
        tag = 'customise_commands'
        opt = f'process.RandomNumberGeneratorService.generator.initialSeed = {jobidx+1}'
        for cmd in cmds:
            if f'--{tag}' not in cmd:
                appendix = f'--{tag} "{opt}"'
                cmd = cmd + ' ' + appendix
            else:
                parts = cmd.split('--')
                idx = [idx for idx, part in enumerate(parts) if part.startswith(tag)][0]
                newpart = parts[idx].rstrip(';" \t\n') + f'; {opt}" '
                parts[idx] = newpart
                cmd = '--'.join(parts)
            this_job_cmds.append(cmd)
        # remove intermediate files if requested
        if args.remove_intermediate_output:
            for stepidx in range(len(cmds)-1):
                rm_cmd = f'rm step{stepidx}.root'
                this_job_cmds.append(rm_cmd)
        job_cmds.append(this_job_cmds)

    # make working directories and executable files
    # note: ideally, would write the executable files in the working directories,
    #       but that does not work with condor if the working directories are on eos...
    #       so instead write them locally (and copy them to the working directory just for reference).
    if os.path.exists(args.workdir) and not args.overwrite:
        raise Exception(f'Working directory {args.workdir} already exists.')
    exes = []
    for jobidx in range(args.number_of_jobs):
        workdir = os.path.abspath(os.path.join(args.workdir, f'job{jobidx}'))
        if not os.path.exists(workdir): os.makedirs(workdir)
        jobscript = os.path.abspath(f'cjob_produce{tagstr}_{jobidx}.sh')
        jobscript_copy = os.path.join(workdir, os.path.basename(jobscript))
        ct.initJobScript(jobscript, cmssw_version=cmssw, proxy=args.proxy)
        with open(jobscript, 'a') as f:
            # go to working directory
            f.write(f'cd {workdir}\n')
            # stop on the first failing command, so a crashed step does not
            # silently fall through to the next one (e.g. a step reading a
            # truncated file left over by a previous, crashed or held attempt)
            # while still letting the job exit 0 in condor.
            f.write('set -e\n')
            # remove any step*.root left over from a previous (e.g. held or
            # crashed) attempt at this same job directory; without this,
            # cmsDriver's output step can fatally fail trying to overwrite
            # a pre-existing file of the same name (observed as a
            # "TStorageFactorySystem::Unlink ... Unsupported" error on EOS).
            f.write('rm -f step*.root\n')
            # write actual commands to run
            for cmd in job_cmds[jobidx]: f.write(cmd+'\n')
        exes.append(jobscript)
        # copy to workdir for reference
        cmd = f'cp {jobscript} {jobscript_copy}'
        os.system(cmd)

    # make job description
    name = f'cjob_produce{tagstr}'
    jobdescriptor = name + '.txt'
    if os.path.exists(jobdescriptor) and not args.overwrite:
        raise Exception('Not yet implemented: job descriptor already exists.')
    ct.makeJobDescription(jobdescriptor, '$(script)', doqueue=False,
        proxy=args.proxy, jobflavour='tomorrow', mem=args.request_memory)
    with open(jobdescriptor, 'a') as f:
        f.write('queue script from(\n')
        for exe in exes: f.write(f'    {exe}\n')
        f.write(')')

    # print output
    print(f'Job working directory {args.workdir} has been prepared.')
    print(f'Check if everything looks fine, then run condor_submit {jobdescriptor} to submit the jobs.')
