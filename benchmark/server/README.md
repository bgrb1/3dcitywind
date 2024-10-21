## Initial setup

Make sure that you have Docker, Kubectl and Google Cloud CLI installed and configured


### Setup GKE cluster

```gcloud container clusters create-auto locust --location=europe-west1-b --project=<project_name>```

### Set kubectl to the GKE cluster

```gcloud container clusters get-credentials locust --location=europe-west1 --project=<project_name>```

We are not sure if this is enough. If not, find out the target context for the GKE cluster


```kubectl config get-contexts```

And switch to the right context 

```kubectl config use-context <context-name>```

### Create artifact repository

```gcloud artifacts repositories create misc --repository-format=docker --location=europe-west1 --project=<project_name>```

### Find out the GKE service account for the project and then give it permission for the artifact repository

```gcloud artifacts repositories add-iam-policy-binding misc --location=europe-west1  --member=serviceAccount:<project_number>-compute@developer.gserviceaccount.com --role="roles/artifactregistry.reader"```


## Prepare benchmark image

### Configuring benchmark configuration

First, decide what you want to benchmark
The options are: static, shifting and random views
Set the benchmark mode in locustfile.py by setting the TASK variable

### Build Docker image
Make sure you run it from this directory with the readme, locustfile etc. 

```docker build -t locust .```

### Tag and push to artifact repository

```docker tag locust europe-west1-docker.pkg.dev/<project_name>/misc/locust:latest```

```docker push europe-west1-docker.pkg.dev/<project_name>/misc/locust:latest```


## Starting locust cluster and run benchmarks

### Start locust-master

```kubectl apply -f locust-master-deployment.yaml```

```kubectl apply -f locust-master-service.yaml```

### Start locust-workers (8 by default, according to locust-worker-deployment.yaml)

```kubectl apply -f locust-worker-deployment.yaml```

### Find out public IP of locust-master for web GUI

```kubectl get all```

### Open web GUI in browser using the locust-master IP and use it to start benchmark

### When you're done, shutdown cluster 

```kubectl delete all --all```







