package main

import (
	"github.com/pulumi/pulumi-aws/sdk/v6/go/aws/codebuild"
	"github.com/pulumi/pulumi-aws/sdk/v6/go/aws/ecr"
	"github.com/pulumi/pulumi-aws/sdk/v6/go/aws/iam"
	"github.com/pulumi/pulumi/sdk/v3/go/pulumi"
	"github.com/pulumi/pulumi/sdk/v3/go/pulumi/config"
)

func main() {
	pulumi.Run(func(ctx *pulumi.Context) error {
		cfg := config.New(ctx, "fireons-cicd")
		githubToken := cfg.RequireSecret("github_token")

		runnerRepo, err := ecr.NewRepository(ctx, "fireons-cicd-runner", &ecr.RepositoryArgs{
			Name:                 pulumi.String("fireons-cicd-runner"),
			ImageTagMutability:   pulumi.String("MUTABLE"),
			ImageScanningConfiguration: &ecr.RepositoryImageScanningConfigurationArgs{
				ScanOnPush: pulumi.Bool(true),
			},
			Tags: pulumi.StringMap{
				"Name": pulumi.String("fireons-cicd-runner"),
			},
		})
		if err != nil {
			return err
		}

		codebuildRole, err := iam.NewRole(ctx, "fireons-codebuild-role", &iam.RoleArgs{
			AssumeRolePolicy: pulumi.String(`{
				"Version": "2012-10-17",
				"Statement": [{
					"Effect": "Allow",
					"Principal": { "Service": "codebuild.amazonaws.com" },
					"Action": "sts:AssumeRole"
				}]
			}`),
			Description: pulumi.String("IAM role for Fireons CodeBuild project"),
		})
		if err != nil {
			return err
		}

		_, err = iam.NewRolePolicyAttachment(ctx, "fireons-codebuild-ecr", &iam.RolePolicyAttachmentArgs{
			Role:      codebuildRole.Name,
			PolicyArn: pulumi.String("arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser"),
		})
		if err != nil {
			return err
		}

		_, err = iam.NewRolePolicy(ctx, "fireons-codebuild-logs", &iam.RolePolicyArgs{
			Role: codebuildRole.Name,
			Policy: pulumi.String(`{
				"Version": "2012-10-17",
				"Statement": [{
					"Effect": "Allow",
					"Action": [
						"logs:CreateLogGroup",
						"logs:CreateLogStream",
						"logs:PutLogEvents"
					],
					"Resource": "*"
				}]
			}`),
		})
		if err != nil {
			return err
		}

		_, err = codebuild.NewSourceCredential(ctx, "fireons-github-credential", &codebuild.SourceCredentialArgs{
			AuthType:   pulumi.String("PERSONAL_ACCESS_TOKEN"),
			ServerType: pulumi.String("GITHUB"),
			Token:      githubToken,
		})
		if err != nil {
			return err
		}

		project, err := codebuild.NewProject(ctx, "fireons-runner", &codebuild.ProjectArgs{
			Name:        pulumi.String("fireons-runner"),
			Description: pulumi.String("Fireons CI/CD runner"),
			ServiceRole: codebuildRole.Arn,
			BuildTimeout: pulumi.Int(60),

			Artifacts: &codebuild.ProjectArtifactsArgs{
				Type: pulumi.String("NO_ARTIFACTS"),
			},

			Environment: &codebuild.ProjectEnvironmentArgs{
				Type:                     pulumi.String("LINUX_CONTAINER"),
				ComputeType:              pulumi.String("BUILD_GENERAL1_SMALL"),
				Image:                    runnerRepo.RepositoryUrl,
				ImagePullCredentialsType: pulumi.String("SERVICE_ROLE"),
				PrivilegedMode:           pulumi.Bool(true),
			},

			Source: &codebuild.ProjectSourceArgs{
				Type:     pulumi.String("GITHUB"),
				Location: pulumi.String("https://github.com/cincotree/fireons.git"),
			},

			LogsConfig: &codebuild.ProjectLogsConfigArgs{
				CloudwatchLogs: &codebuild.ProjectLogsConfigCloudwatchLogsArgs{
					GroupName: pulumi.String("fireons-codebuild"),
					StreamName: pulumi.String("build"),
					Status:    pulumi.String("ENABLED"),
				},
			},

			Tags: pulumi.StringMap{
				"Name": pulumi.String("fireons-runner"),
			},
		})
		if err != nil {
			return err
		}

		ctx.Export("codebuild_project_name", project.Name)
		ctx.Export("codebuild_project_arn", project.Arn)
		ctx.Export("ecr_runner_uri", runnerRepo.RepositoryUrl)

		return nil
	})
}
