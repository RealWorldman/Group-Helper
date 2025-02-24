#!/bin/bash

# Deploy to Google App Engine
gcloud builds submit --config cloudbuild_vm.yaml group-helper-app/.