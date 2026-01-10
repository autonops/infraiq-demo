#!/bin/bash
cd ~/Documents/infraiq-demo
docker build -t autonops/infraiq-demo-api:latest -f api/Dockerfile .
docker push autonops/infraiq-demo-api:latest
echo "✅ Pushed. Now run on VM: ./deploy.sh"
