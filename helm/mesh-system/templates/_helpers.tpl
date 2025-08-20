{{/*
Expand the name of the chart.
*/}}
{{- define "mesh-system.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "mesh-system.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "mesh-system.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "mesh-system.labels" -}}
helm.sh/chart: {{ include "mesh-system.chart" . }}
{{ include "mesh-system.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "mesh-system.selectorLabels" -}}
app.kubernetes.io/name: {{ include "mesh-system.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "mesh-system.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "mesh-system.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the database URL
*/}}
{{- define "mesh-system.databaseUrl" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "postgresql+asyncpg://%s:%s@%s-postgresql:5432/%s" .Values.postgresql.auth.username .Values.postgresql.auth.password .Release.Name .Values.postgresql.auth.database }}
{{- else }}
{{- .Values.secrets.databaseUrl }}
{{- end }}
{{- end }}

{{/*
Create the Redis URL
*/}}
{{- define "mesh-system.redisUrl" -}}
{{- if .Values.redis.enabled }}
{{- printf "redis://%s-redis-master:6379" .Release.Name }}
{{- else }}
{{- printf "redis://redis-service:6379" }}
{{- end }}
{{- end }}

{{/*
Create the ChromaDB host
*/}}
{{- define "mesh-system.chromaHost" -}}
{{- if .Values.chromadb.enabled }}
{{- printf "%s-chromadb" .Release.Name }}
{{- else }}
{{- printf "chromadb-service" }}
{{- end }}
{{- end }}

{{/*
Create the Ollama URL
*/}}
{{- define "mesh-system.ollamaUrl" -}}
{{- if .Values.ollama.enabled }}
{{- printf "http://%s-ollama:11434" .Release.Name }}
{{- else }}
{{- printf "http://ollama-service:11434" }}
{{- end }}
{{- end }}