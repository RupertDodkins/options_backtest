# Installation

`pip install -e .`

# Linking to QuantConnect
Based of these instructions
https://www.quantconnect.com/docs/v2/lean-cli/projects/libraries/project-libraries

```
cd /Users/username/options_backtest
lean project-create "Library/optionsbacktest" --language python # can't have an underscore in the name on quantconnect
cp /Users/username/options_backtest/src/options_backtest/* ./Library/optionsbacktest 
lean library add 'Backtest 20230601' 'Library/optionsbacktest'
```

## Remote -> local
```
lean cloud pull --project 'Backtest 20230601'
cp ./Library/optionsbacktest /Users/username/options_backtest/src/options_backtest/*
```

## local -> remote
```
cp /Users/username/options_backtest/src/options_backtest/* ./Library/optionsbacktest
lean cloud push --project 'Backtest 20230601'
```
