/**
 * @file index.ts
 * Barrel export for all sidebar UI component fragments, so
 * sidebarRenderer.ts can import them from a single path.
 */

export { renderStatusSection } from './statusSection';
export { renderSessionControls } from './sessionControls';
export { renderMetricsSection } from './metricsSection';
export { renderEventsSection } from './eventsSection';
export { renderHintsSection } from './hintsSection';
export { renderCounterexampleSection } from './counterexampleSection';
export { renderSparklineSection } from './sparklineSection';
export { renderRecommendationSection } from './recommendationSection';
export { renderEndSection } from './endSection';
export { getClientScript } from './clientScript';
