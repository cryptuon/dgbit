<template>
  <article class="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
    <div class="flex items-center justify-between">
      <h4 class="font-semibold">{{ job.type }}</h4>
      <span
        class="rounded-full px-3 py-1 text-xs font-semibold uppercase"
        :class="statusColor"
      >
        {{ job.status }}
      </span>
    </div>
    <dl class="mt-4 space-y-1 text-sm text-slate-400">
      <div class="flex justify-between">
        <dt>Created</dt>
        <dd>{{ new Date(job.created_at).toLocaleString() }}</dd>
      </div>
      <div class="flex justify-between">
        <dt>Payload</dt>
        <dd class="font-mono text-xs">{{ payloadString }}</dd>
      </div>
    </dl>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";

interface JobCardProps {
  job: {
    id: string;
    type: string;
    status: string;
    created_at: string;
    payload: Record<string, unknown>;
  };
}

const props = defineProps<JobCardProps>();

const statusColor = computed(() => {
  switch (props.job.status) {
    case "completed":
      return "bg-emerald-500/20 text-emerald-300";
    case "failed":
      return "bg-rose-500/20 text-rose-300";
    case "running":
      return "bg-amber-500/20 text-amber-300";
    default:
      return "bg-slate-700 text-slate-300";
  }
});

const payloadString = computed(() => JSON.stringify(props.job.payload));
</script>
