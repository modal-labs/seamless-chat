#!/bin/bash

cd frontend
npm run build
cd ..
MODAL_ENVIRONMENT=vishy-dev modal deploy seamless.py