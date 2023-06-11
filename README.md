
conda activate stocks
lean cloud push --project '/Users/dodkins/PythonProjects/stocks/options_testing'  -- does this work

# Initial setup
I had some success using this
https://www.quantconnect.com/docs/v2/lean-cli/projects/libraries/project-libraries
cd /Users/dodkins/PythonProjects/stocks/RupeDogIndustries
lean project-create "Library/optionstesting" --language python
cp /Users/dodkins/PythonProjects/stocks/options_testing/options_testing/* ./Library/optionstesting ## can't have an underscore in the name on quantconnect
lean library add 'Tesla LEAPS' 'Library/optionstesting'

# Remote -> local
lean cloud pull --project 'Tesla LEAPS'
cp ./Library/optionstesting /Users/dodkins/PythonProjects/stocks/options_testing/options_testing/*

# local -> remote
cp /Users/dodkins/PythonProjects/stocks/options_testing/options_testing/* ./Library/optionstesting
lean cloud push --project 'Tesla LEAPS'
