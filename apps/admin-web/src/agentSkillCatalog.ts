const consumers = new Set<() => Promise<void>>();

export function subscribeAgentSkillCatalog(refresh: () => Promise<void>) {
  consumers.add(refresh);
  return () => { consumers.delete(refresh); };
}

export async function refreshAgentSkillCatalogConsumers() {
  const results = await Promise.allSettled([...consumers].map(refresh => refresh()));
  const failure = results.find(result => result.status === "rejected");
  if (failure?.status === "rejected") throw failure.reason;
}
