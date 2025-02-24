#!/bin/bash

# Deploy to Google App Engine
gcloud builds submit --config cloudbuild_group_helper_vm.yaml group-helper-app/.