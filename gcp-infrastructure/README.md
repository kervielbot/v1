How to re-set up after creating a new project:

- From the Console, create a new Cloud Storage bucket in the project. It needs to have a globally unique name, you can put the project ID as bucket name.
- Once created, put that bucket name in backend.tf and terraform.tfvars
- Run `terraform init`
- Run `terraform apply`
