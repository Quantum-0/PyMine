#!/bin/bash
requiredver="3.7.9"
for command in pypy3 pypy python3.9 python3.8 python3.7 python3 python
do

currentver=$($command -c "import platform;print(platform.python_version())")
if [ "$(printf '%s\n' "$requiredver" "$currentver" | sort -V | head -n1)" = "$requiredver" ]; then
        echo "Using Python version $currentver ($command)"
        $command pymine
        exit 0
fi

done

echo "Couldn't find suitable Python version. Please use your package manager to install Python 3.7.9 or later"
exit 1
