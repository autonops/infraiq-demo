# =============================================================================
# InfraIQ Demo Server - GCP Infrastructure
# =============================================================================

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "intense-grove-451422-s6"
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "us-central1-a"
}

resource "google_compute_address" "demo_server" {
  name   = "demo-server-ip"
  region = var.region
}

resource "google_compute_firewall" "demo_server" {
  name    = "demo-server-allow-web"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["demo-server"]
}

resource "google_compute_instance" "demo_server" {
  name         = "demo-server"
  machine_type = "e2-small"
  zone         = var.zone

  tags = ["demo-server"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2404-lts-amd64"
      size  = 30
      type  = "pd-balanced"
    }
  }

  network_interface {
    network = "default"
    access_config {
      nat_ip = google_compute_address.demo_server.address
    }
  }

  metadata = {
    ssh-keys = "jasonboykin:${file("~/.ssh/id_rsa.pub")}"
  }

  metadata_startup_script = <<-EOF
    #!/bin/bash
    set -e
    
    # Install Docker
    curl -fsSL https://get.docker.com | sh
    usermod -aG docker jasonboykin
    
    # Install Docker Compose
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    
    # Install Caddy
    apt-get update
    apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
    apt-get update
    apt-get install -y caddy
    
    # Create app directory
    mkdir -p /opt/infraiq-demo
    chown jasonboykin:jasonboykin /opt/infraiq-demo
    
    echo "Setup complete!"
  EOF

  service_account {
    scopes = ["cloud-platform"]
  }

  allow_stopping_for_update = true
}

output "demo_server_ip" {
  value       = google_compute_address.demo_server.address
  description = "Static IP address for demo.autonops.io"
}

output "ssh_command" {
  value       = "gcloud compute ssh demo-server --zone us-central1-a"
  description = "SSH command to connect to the server"
}
