How to re-set up after creating a new project:

- From the Console, create a new Cloud Storage bucket in the project. It needs to have a globally unique name, you can put the project ID as bucket name.
- Once created, put that bucket name in backend.tf and terraform.tfvars
- Grant yourself Service Usage Admin role from the Console
- Manually enable the Compute service via the Console: https://console.cloud.google/apis/library/compute.googleapis.com?csesidx=1374927668&project=<NEW PROJECT ID>
- Run `terraform init`
- Run `terraform apply`
- Update your gcloud config:
    - gcloud config set project <NEW PROJECT ID>
    - gcloud auth application-default set-quota-project <NEW PROJECT ID>
