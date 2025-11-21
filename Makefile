.PHONY: build deploy clean

build:
	@echo "Building Backend (Python)..."
	docker build -t netauto-backend:latest -f deploy/Dockerfile.backend .
	@echo "Building Frontend..."
	docker build -t netauto-frontend:latest -f deploy/Dockerfile.frontend .
	@echo "Building Microservice..."
	docker build -t netauto-microservice:latest network-microservice/
	@echo "Building Linux Device..."
	docker build -t netauto-linux-device:latest -f deploy/Dockerfile.linux-device .

redeploy-k8s:
	@echo "Deleting and Redeploying K8s resources..."
	kubectl delete -f k8s/linux-device.yaml --ignore-not-found=true
	kubectl delete -f k8s/network-microservice.yaml --ignore-not-found=true
	kubectl delete -f k8s/frontend.yaml --ignore-not-found=true
	kubectl delete -f k8s/backend.yaml --ignore-not-found=true
	kubectl delete -f k8s/services.yaml --ignore-not-found=true
	kubectl delete -f k8s/pvc.yaml --ignore-not-found=true

	kubectl apply -f k8s/pvc.yaml
	kubectl apply -f k8s/services.yaml
	kubectl apply -f k8s/backend.yaml
	kubectl apply -f k8s/frontend.yaml
	kubectl apply -f k8s/network-microservice.yaml
	kubectl apply -f k8s/linux-device.yaml

clean-k8s:
	@echo "Deleting K8s resources..."
	kubectl delete -f k8s/linux-device.yaml --ignore-not-found=true
	kubectl delete -f k8s/network-microservice.yaml --ignore-not-found=true
	kubectl delete -f k8s/frontend.yaml --ignore-not-found=true
	kubectl delete -f k8s/backend.yaml --ignore-not-found=true
	kubectl delete -f k8s/services.yaml --ignore-not-found=true
	kubectl delete -f k8s/pvc.yaml --ignore-not-found=true



deploy:
	@echo "Applying K8s manifests..."
	kubectl apply -f k8s/pvc.yaml
	kubectl apply -f k8s/services.yaml
	kubectl apply -f k8s/backend.yaml
	kubectl apply -f k8s/frontend.yaml
	kubectl apply -f k8s/network-microservice.yaml
	kubectl apply -f k8s/linux-device.yaml

all: build deploy

clean:
	@echo "Deleting K8s resources..."
	kubectl delete -f k8s/linux-device.yaml
	kubectl delete -f k8s/network-microservice.yaml
	kubectl delete -f k8s/frontend.yaml
	kubectl delete -f k8s/backend.yaml
	kubectl delete -f k8s/services.yaml
	kubectl delete -f k8s/pvc.yaml