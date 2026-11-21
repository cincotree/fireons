data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_ecr_repository" "jobs" {
  name                 = "${local.name}-jobs"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "jobs" {
  repository = aws_ecr_repository.jobs.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the 5 most recent images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_ecs_cluster" "jobs" {
  name = "${local.name}-jobs"
}

resource "aws_security_group" "jobs" {
  name        = "${local.name}-jobs"
  description = "Egress only security group for Fargate job tasks"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

data "aws_iam_policy_document" "ecs_tasks_trust" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "jobs_execution" {
  name               = "${local.name}-jobs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_trust.json
}

resource "aws_iam_role_policy_attachment" "jobs_execution" {
  role       = aws_iam_role.jobs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "jobs_task" {
  name               = "${local.name}-jobs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_trust.json
}

data "aws_iam_policy_document" "jobs_task" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.this.arn]
  }
}

resource "aws_iam_role_policy" "jobs_task" {
  name   = "read-secret"
  role   = aws_iam_role.jobs_task.id
  policy = data.aws_iam_policy_document.jobs_task.json
}

resource "aws_cloudwatch_log_group" "jobs" {
  name              = "/ecs/${local.name}-jobs"
  retention_in_days = 14
}

resource "aws_ecs_task_definition" "jobs" {
  family                   = local.jobs_family
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.jobs_execution.arn
  task_role_arn            = aws_iam_role.jobs_task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  container_definitions = jsonencode([{
    name      = "jobs"
    image     = "${aws_ecr_repository.jobs.repository_url}:latest"
    essential = true
    environment = [
      { name = "APP_ENV", value = var.environment },
      { name = "DB_NULL_POOL", value = "true" },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.jobs.name
        awslogs-region        = var.region
        awslogs-stream-prefix = "jobs"
      }
    }
  }])
}
