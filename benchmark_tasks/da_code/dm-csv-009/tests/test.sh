#!/bin/bash
mkdir -p /logs/verifier

python /tests/test_outputs.py 2>&1 | tee /logs/verifier/test-stdout.txt

if [ ! -s /logs/verifier/reward.txt ]; then
    echo 0 > /logs/verifier/reward.txt
fi
exit 0
