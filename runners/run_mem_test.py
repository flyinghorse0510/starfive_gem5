import build_tool as buildTool
import util
import argparse, os, sys

if __name__ == "__main__":
    
    rootRepoPath = util.get_repo_root()
    if rootRepoPath is None:
        raise Exception("Git repo not found!")
    
    sys.path.insert(0, "%s/runners/mem_test" %(rootRepoPath))
    from mem_test import MemTestGenerator as dataGenerator
    from mem_test import MemTestTranslator as dataTranslator
    
    parser = argparse.ArgumentParser(
                    prog='StarFive Test Runners (MemTest)',
                    description='StarFive MemTest')
    # Subcommand Parser
    subcmdParser = parser.add_subparsers(dest='subcmd', required=True)
    buildParser = subcmdParser.add_parser("build", help="Build gem-5 simulator")
    memTestParser = subcmdParser.add_parser("test", help="Perform gem-5 memory test")
    dataGenParser = subcmdParser.add_parser("generate", help="Generate gem-5 memory test data")
    dataTransParser = subcmdParser.add_parser("translate", help="Translate gem-5 memory test data into readable format")
    ## Build subcommand parser
    buildTool.customize_build(buildParser)
    dataGenerator.customize_generator(dataGenParser)
    dataTranslator.customize_translator(dataTransParser)
    
    # Parse commands
    options = parser.parse_args()
    # Assign root repo path
    options.rootRepoPath = rootRepoPath
    # Invoke subcommands
    if options.subcmd == "build":
        # Build simulators
        buildTool.build(options)
    elif options.subcmd == "generate":
        # Create directory
        if options.output_path is None or options.output_path == "":
            options.output_path = "%s/runners/mem_test/data" %(options.rootRepoPath)
        
        options.path = "%s/%s" %(options.output_path, options.output_file)
        util.create_dir(options.output_path)
        
        # Generate data
        dataGenerator.generate(options)
        
    elif options.subcmd == "translate":
        # Translate data
        dataTranslator.translate_binary("%s/runners/mem_test/data/mem_test_data.bin" %(options.rootRepoPath), "%s/runners/mem_test/data/mem_test_data.txt" %(options.rootRepoPath))
        
        
    