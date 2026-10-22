variable "region" {
  type    = string
  default = "ap-southeast-1"
}

variable "github_repository" {
  type    = string
  default = "cincotree/fireons"
}

variable "github_environment" {
  type    = string
  default = "production"
}

variable "root_domain" {
  type    = string
  default = "fireons.com"
}

variable "alarm_email" {
  type = string
}

variable "deploy_role_policy_arns" {
  type    = list(string)
  default = []
}

variable "budget_thresholds_usd" {
  type    = list(number)
  default = [1, 10]
}
