# stacksmith — VPS provisioning as code.
#
# Supports two providers: Hetzner Cloud (default) and DigitalOcean.
# Select with the `provider` variable.
#
# Usage:
#   terraform init
#   terraform apply \
#     -var="provider=hcloud" \
#     -var="hcloud_token=..." \
#     -var="ssh_key_name=..."
#   # or
#   terraform apply \
#     -var="provider=digitalocean" \
#     -var="do_token=..." \
#     -var="ssh_key_name=..."

terraform {
  required_version = ">= 1.6"
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.45"
    }
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.30"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
  }
}

# --- Variables ---

variable "provider" {
  description = "Cloud provider: hcloud or digitalocean"
  type        = string
  default     = "hcloud"
}

variable "hcloud_token" {
  description = "Hetzner Cloud API token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "do_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "server_name" {
  description = "Name of the VPS"
  type        = string
  default     = "docubot-prod"
}

variable "server_type" {
  description = "Server size (provider-specific defaults below)"
  type        = string
  default     = ""
}

variable "location" {
  description = "Datacenter region"
  type        = string
  default     = ""
}

variable "ssh_key_name" {
  description = "Name of the SSH key (must be uploaded to the provider)"
  type        = string
}

variable "domain" {
  description = "Domain for TLS (optional)"
  type        = string
  default     = ""
}

variable "cost_vps_monthly_usd" {
  description = "Monthly cost for the cost metric"
  type        = string
  default     = "8.0"
}

# --- Provider configuration (only the selected provider is activated) ---

provider "hcloud" {
  token = var.hcloud_token
}

provider "digitalocean" {
  token = var.do_token
}

# --- Hetzner Cloud resources ---

data "hcloud_ssh_key" "hcloud_key" {
  count = var.provider == "hcloud" ? 1 : 0
  name  = var.ssh_key_name
}

resource "hcloud_firewall" "hcloud_fw" {
  count = var.provider == "hcloud" ? 1 : 0
  name  = "${var.server_name}-fw"

  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "3000"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
}

resource "hcloud_server" "hcloud_server" {
  count        = var.provider == "hcloud" ? 1 : 0
  name         = var.server_name
  server_type  = coalesce(var.server_type, "cx22")
  location     = coalesce(var.location, "nbg1")
  image        = "ubuntu-24.04"
  ssh_keys     = [data.hcloud_ssh_key.hcloud_key[0].id]
  firewall_ids = [hcloud_firewall.hcloud_fw[0].id]
  user_data    = templatefile("${path.module}/cloud-init.yml", { domain = var.domain })
  labels = {
    project = "stacksmith"
    role    = "prod"
  }
}

# --- DigitalOcean resources ---

data "digitalocean_ssh_key" "do_key" {
  count = var.provider == "digitalocean" ? 1 : 0
  name  = var.ssh_key_name
}

resource "digitalocean_firewall" "do_fw" {
  count = var.provider == "digitalocean" ? 1 : 0
  name  = "${var.server_name}-fw"

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }
  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }
  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }
  inbound_rule {
    protocol         = "tcp"
    port_range       = "3000"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }
}

resource "digitalocean_droplet" "do_server" {
  count    = var.provider == "digitalocean" ? 1 : 0
  name     = var.server_name
  size     = coalesce(var.server_type, "s-2vcpu-4gb")
  region   = coalesce(var.location, "fra1")
  image    = "ubuntu-24-04"
  ssh_keys = [data.digitalocean_ssh_key.do_key[0].id]
  user_data = templatefile("${path.module}/cloud-init.yml", { domain = var.domain })
  tags     = ["stacksmith", "prod"]
}

resource "digitalocean_firewall_attachment" "do_fw_attach" {
  count      = var.provider == "digitalocean" ? 1 : 0
  firewall_id = digitalocean_firewall.do_fw[0].id
  droplet_ids = [digitalocean_droplet.do_server[0].id]
}

# --- Outputs (unified across providers) ---

output "server_ip" {
  value = var.provider == "hcloud" ? hcloud_server.hcloud_server[0].ipv4_address : digitalocean_droplet.do_server[0].ipv4_address
}

output "ssh_command" {
  value = "ssh root@${var.provider == "hcloud" ? hcloud_server.hcloud_server[0].ipv4_address : digitalocean_droplet.do_server[0].ipv4_address}"
}

resource "local_file" "deploy_to_vps" {
  content = templatefile("${path.module}/deploy-to-vps.sh.tpl", {
    server_ip = var.provider == "hcloud" ? hcloud_server.hcloud_server[0].ipv4_address : digitalocean_droplet.do_server[0].ipv4_address
  })
  filename = "${path.module}/../scripts/deploy-to-vps.sh"
}
