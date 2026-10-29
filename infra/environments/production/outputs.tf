output "github_environment_variables" {
  value = module.fireons.github_environment_variables
}

output "certificate_validation_records" {
  value = module.fireons.certificate_validation_records
}

output "webapp_url" {
  value = module.fireons.webapp_url
}

output "api_base_url" {
  value = module.fireons.api_base_url
}

output "webapp_distribution_domain_name" {
  value = module.fireons.webapp_distribution_domain_name
}

output "api_distribution_domain_name" {
  value = module.fireons.api_distribution_domain_name
}

output "secret_arn" {
  value = module.fireons.secret_arn
}
