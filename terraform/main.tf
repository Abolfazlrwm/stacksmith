# stacksmith — VPS provisioning as code.
#
# This module provisions a single VPS, opens the firewall, and writes a
# deploy script that SSHs in and runs the stack. It is intentionally
# provider-agnostic: the default is Hetzner Cloud (cheap, simple), but
# the module structure supports swapping to DigitalOcean or AWS by
# changing the provider block.

terraform {
  required_version = ">= 1.6"
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.45"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
  }
}

variable "hcloud_token" {
  description = "Hetzner Cloud API token"
  type        = string
  sensitive   = true
}

variable "server_name" {
  description = "Name of the VPS"
  type        = string
  default     = "docubot-prod"
}

variable "server_type" {
  description = "Hetzner server type (cx22 = 2 vCPU / 4 GB)"
  type        = string
  default     = "cx22"
}

variable "location" {
  description = "Hetzner datacenter"
  type        = string
  default     = "nbg1"
}

variable "ssh_key_name" {
  description = "Name of the SSH key in Hetzner Cloud"
  type        = string
}

variable "domain" {
  description = "Domain for the docubot stack (for DNS and TLS)"
  type        = string
  default     = ""
}

provider "hcloud" {
  token = var.hcloud_token
}

# SSH key (must be uploaded to Hetzner Cloud separately)
data "hcloud_ssh_key" "deploy" {
  name = var.ssh_key_name
}

# Firewall: allow SSH (22), HTTP (80), HTTPS (443), and monitoring (3000)
# from anywhere. All other ports are closed.
resource "hcloud_firewall" "stacksmith" {
  name = "${var.server_name}-fw"

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "22"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }

  # Monitoring (Grafana) — restrict to a known IP in production.
  rule {
    direction = "in"
    protocol  = "tcp"
    port      = "3000"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
}

# The VPS
resource "hcloud_server" "stacksmith" {
  name        = var.server_name
  server_type = var.server_type
  location    = var.location
  image       = "ubuntu-24.04"
  ssh_keys    = [data.hcloud_ssh_key.deploy.id]
  firewall_ids = [hcloud_firewall.stacksmith.id]

  labels = {
    project = "stacksmith"
    role    = "prod"
  }

  # Provision Docker and docker-compose on first boot.
  user_data = templatefile("${path.module}/cloud-init.yml", {
    domain = var.domain
  })
}

output "server_ip" {
  value = hcloud_server.stacksmith.ipv4_address
}

output "server_ipv6" {
  value = hcloud_server.stacksmith.ipv6_address
}

output "ssh_command" {
  value = "ssh root@${hcloud_server.stacksmith.ipv4_address}"
}

# Write a deploy script that clones the repo and brings up the stack.
resource "local_file" "deploy_to_vps" {
  content = templatefile("${path.module}/deploy-to-vps.sh", {
    server_ip = hcloud_server.stacksmith.ipv4_address
  })
  filename = "${path.module}/../scripts/deploy-to-vps.sh"
}
