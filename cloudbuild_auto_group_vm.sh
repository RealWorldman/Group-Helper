#!/bin/bash

# Deploy to Google App Engine
gcloud builds submit --config cloudbuild_auto_group_vm.yaml auto-group-app/.