variable "function_name"    { type = string }
variable "zip_path"         { type = string }
variable "handler"          { type = string }
variable "role_arn"         { type = string }
variable "timeout"          { type = number; default = 30 }
variable "memory_mb"        { type = number; default = 256 }
variable "log_retention"    { type = number; default = 14 }
variable "environment_vars" { type = map(string); default = {} }
