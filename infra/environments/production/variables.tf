variable "region" {
  type    = string
  default = "ap-southeast-1"
}

variable "github_repository" {
  type    = string
  default = "cincotree/fireons"
}

variable "webapp_domain" {
  type    = string
  default = "app.fireons.com"
}

variable "api_domain" {
  type    = string
  default = "api.fireons.com"
}

variable "budget_email" {
  type = string
}

variable "budget_thresholds_usd" {
  type    = list(number)
  default = [1, 10]
}

variable "enable_custom_domains" {
  type    = bool
  default = false
}

variable "lambda_web_adapter_layer_arn" {
  type    = string
  default = "arn:aws:lambda:ap-southeast-1:753240598075:layer:LambdaAdapterLayerArm64:25"
}

variable "api_reserved_concurrency" {
  type    = number
  default = 3
}

variable "captcha_enabled" {
  type    = bool
  default = true
}
