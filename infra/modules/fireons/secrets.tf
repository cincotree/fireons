resource "aws_secretsmanager_secret" "this" {
  name                    = "${var.project}/${var.environment}"
  recovery_window_in_days = 7
}
