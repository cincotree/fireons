variable "project" {
  type    = string
  default = "fireons"
}

variable "environment" {
  type = string
}

variable "region" {
  type = string
}

variable "github_repository" {
  type = string
}

variable "github_oidc_provider_arn" {
  type = string
}

variable "webapp_domain" {
  type = string
}

variable "api_domain" {
  type = string
}

variable "enable_custom_domains" {
  type    = bool
  default = false
}

variable "lambda_web_adapter_layer_arn" {
  type = string
}

variable "api_reserved_concurrency" {
  type = number
}

variable "invite_only" {
  type = bool
}
