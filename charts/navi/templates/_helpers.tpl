{{- define "navi.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "navi.fullname" -}}
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

{{- define "navi.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "navi.labels" -}}
helm.sh/chart: {{ include "navi.chart" . }}
app.kubernetes.io/name: {{ include "navi.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/* Selector labels for one component: include "navi.selectorLabels" (list . "backend") */}}
{{- define "navi.selectorLabels" -}}
{{- $root := index . 0 -}}
app.kubernetes.io/name: {{ include "navi.name" $root }}
app.kubernetes.io/instance: {{ $root.Release.Name }}
app.kubernetes.io/component: {{ index . 1 }}
{{- end }}

{{- define "navi.tag" -}}
{{- .Values.image.tag | default .Chart.AppVersion | default "latest" }}
{{- end }}

{{- define "navi.backendImage" -}}
{{- printf "%s:%s" .Values.image.backend (include "navi.tag" .) }}
{{- end }}

{{- define "navi.frontendImage" -}}
{{- printf "%s:%s" .Values.image.frontend (include "navi.tag" .) }}
{{- end }}

{{- define "navi.secretName" -}}
{{- .Values.existingSecret | default (printf "%s-secrets" (include "navi.fullname" .)) }}
{{- end }}

{{- define "navi.postgresHost" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgres" (include "navi.fullname" .) }}
{{- else }}
{{- required "externalDatabase.host is required when postgresql.enabled is false" .Values.externalDatabase.host }}
{{- end }}
{{- end }}

{{- define "navi.postgresPort" -}}
{{- if .Values.postgresql.enabled }}5432{{ else }}{{ .Values.externalDatabase.port }}{{ end }}
{{- end }}

{{- define "navi.postgresUser" -}}
{{- if .Values.postgresql.enabled }}{{ .Values.postgresql.user }}{{ else }}{{ .Values.externalDatabase.user }}{{ end }}
{{- end }}

{{- define "navi.postgresDatabase" -}}
{{- if .Values.postgresql.enabled }}{{ .Values.postgresql.database }}{{ else }}{{ .Values.externalDatabase.database }}{{ end }}
{{- end }}

{{/* envFrom shared by the backend and the migration init container */}}
{{- define "navi.envFrom" -}}
- configMapRef:
    name: {{ include "navi.fullname" . }}-config
- secretRef:
    name: {{ include "navi.secretName" . }}
{{- end }}

{{/* Restart pods when the chart-managed config or secret changes */}}
{{- define "navi.configChecksum" -}}
checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
{{- if not .Values.existingSecret }}
checksum/secret: {{ include (print $.Template.BasePath "/secret.yaml") . | sha256sum }}
{{- end }}
{{- end }}
