/**
 * @file EventTimeline.ts
 * Unified chronological event array — the single timeline that both
 * automatic and manual events share. One array, one schema.
 */

import { EventType, TimelineEvent } from '../types';

export class EventTimeline {
  private readonly events: TimelineEvent[] = [];
  private readonly sessionStartTime: number;

  /**
   * @param startTime - Date.now() at session start (epoch ms)
   */
  constructor(startTime: number) {
    this.sessionStartTime = startTime;
  }

  /**
   * Push an event to the timeline with auto-computed elapsed time.
   * @param event - The event type
   * @param meta - Optional metadata (chars count, error message, etc.)
   * @returns The created TimelineEvent entry
   */
  push(event: EventType, meta?: Record<string, unknown>): TimelineEvent {
    const entry: TimelineEvent = {
      time: this.getElapsedSeconds(),
      event,
    };
    if (meta !== undefined) {
      entry.meta = meta;
    }
    this.events.push(entry);
    return entry;
  }

  /**
   * Get seconds elapsed since session start.
   * Used for timeline timestamps and timer display.
   */
  getElapsedSeconds(): number {
    return Math.round((Date.now() - this.sessionStartTime) / 1000);
  }

  /** Get the raw session start timestamp (epoch ms) */
  getStartTime(): number {
    return this.sessionStartTime;
  }

  /** Get all events (read-only view) */
  getEvents(): ReadonlyArray<TimelineEvent> {
    return this.events;
  }

  /** Filter events by type */
  getEventsByType(type: EventType): TimelineEvent[] {
    return this.events.filter((e) => e.event === type);
  }

  /** Count occurrences of a specific event type */
  getEventCount(type: EventType): number {
    return this.events.filter((e) => e.event === type).length;
  }

  /** Serialize the timeline array for JSON output */
  toJSON(): TimelineEvent[] {
    return [...this.events];
  }

  /**
   * Restore a timeline from saved data (crash recovery).
   * @param events - Previously saved timeline events
   * @param startTime - Original session start timestamp
   */
  static fromJSON(events: TimelineEvent[], startTime: number): EventTimeline {
    const timeline = new EventTimeline(startTime);
    for (const event of events) {
      timeline.events.push({ ...event });
    }
    return timeline;
  }
}
