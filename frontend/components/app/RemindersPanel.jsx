// RemindersPanel.jsx
import { useState, useEffect, useCallback } from "react";
import { Trash2, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import cronstrue from 'cronstrue';
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion";
import {
  Popover,
  PopoverContent,
  PopoverDescription,
  PopoverHeader,
  PopoverTitle,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar"

export default function RemindersPanel() {
  const [remindersDoc, setRemindersDoc] = useState(null);
  const [loading, setLoading] = useState(false);
  const [savingId, setSavingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const [minutes, setMinutes] = useState(0);
  const [hours, setHours] = useState(0);
  const [days, setDays] = useState(0);

  const [skipDate, setSkipDate] = useState(new Date());
  const [exprDate, setExprDate] = useState(new Date());
  const [skipHour, setSkipHour] = useState(0);
  const [exprHour, setExprHour] = useState(0);
  const [skipMinute, setSkipMinute] = useState(0);
  const [exprMinute, setExprMinute] = useState(0);

  const [openSkipCal, setOpenSkipCal] = useState(false);
  const handleOpenSkipCal = () => {
    setOpenSkipCal((prev) => !prev);
  };

  const [openExprCal, setOpenExprCal] = useState(false);
  const handleOpenExprCal = () => {
    setOpenExprCal((prev) => !prev);
  };

  const setSnoozeFields = ({ m, h, d }) => {
    setMinutes(m);
    setHours(h);
    setDays(d);
  };

  const handleSnooze = async (reminder) => {
    const m = Number(minutes) || 0;
    const h = Number(hours) || 0;
    const d = Number(days) || 0;

    const now = new Date();
    const totalMinutes = m + h * 60 + d * 24 * 60;
    const snoozeUntil = new Date(now.getTime() + totalMinutes * 60 * 1000);
    const iso = snoozeUntil.toISOString();

    try {
      await fetch(`/api/reminders/${reminder.id}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "snooze",
          snooze_until: iso,
        }),
      });
      fetchReminders();
    } catch (err) {
      console.error("Error snoozing reminder", err);
    }
  };

  async function handleClearSnooze(reminder) {
    try {
      await fetch(`/api/memory/reminders/${reminder.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ snooze_until: null }),
      });
      fetchReminders();
    } catch (err) {
      console.error("Failed to clear snooze", err);
    }
  }

  const handleSkip = async (reminder) => {
    if (!skipDate) return;

    const date = new Date(skipDate);
    const h = Number(skipHour) || 0;
    const m = Number(skipMinute) || 0;

    date.setHours(h);
    date.setMinutes(m);
    date.setSeconds(0);
    date.setMilliseconds(0);

    const iso = date.toISOString();

    try {
      await fetch(`/api/reminders/${reminder.id}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "skip",
          skip_until: iso,
        }),
      });
      setOpenSkipCal(false);
      fetchReminders();
    } catch (err) {
      console.error("Error skipping reminder", err);
    }
  };

  async function handleClearSkip(reminder) {
    try {
      // 1) Clear skip_until
      await fetch(`/api/memory/reminders/${reminder.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skip_until: null }),
      });

      // 2) Force a toggle cycle to recalc early_notification
      // First, disable (if not already)
      await fetch(`/api/reminders/${reminder.id}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "toggle",
          status: "disabled",
        }),
      });

      // Then re-enable
      await fetch(`/api/reminders/${reminder.id}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "toggle",
          status: "enabled",
        }),
      });

      fetchReminders();
    } catch (err) {
      console.error("Failed to clear skip", err);
      fetchReminders();
    }
  }

  const handleSetExpiration = async (reminder) => {
    if (!exprDate) return;

    const date = new Date(exprDate);
    const h = Number(exprHour) || 0;
    const m = Number(exprMinute) || 0;

    date.setHours(h);
    date.setMinutes(m);
    date.setSeconds(0);
    date.setMilliseconds(0);

    const iso = date.toISOString();

    try {
      await fetch(`/api/memory/reminders/${reminder.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ends_on: iso,
        }),
      });
      setOpenExprCal(false);
      fetchReminders();
    } catch (err) {
      console.error("Error setting expiration", err);
    }
  };

  async function handleClearExpiration(reminder) {
    try {
      await fetch(`/api/memory/reminders/${reminder.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ends_on: null }),
      });
      fetchReminders();
    } catch (err) {
      console.error("Failed to clear expiration", err);
    }
  }

  const fetchReminders = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/memory/reminders");
      const data = await res.json();
      setRemindersDoc(data);
    } catch (err) {
      console.error("Failed to fetch reminders", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let intervalId;

    fetchReminders();
    intervalId = setInterval(fetchReminders, 30000);

    return () => clearInterval(intervalId);
  }, [fetchReminders]);

  if (loading && !remindersDoc) {
    return <div className="text-xs text-muted-foreground">Loading reminders…</div>;
  }

  if (
    !remindersDoc ||
    !remindersDoc.entries ||
    remindersDoc.entries.length === 0
  ) {
    return <div className="text-xs text-muted-foreground">No reminders yet.</div>;
  }

  const entries = remindersDoc.entries;

  async function handleToggleStatus(reminder) {
    const newStatus =
      reminder.status === "disabled" ? "enabled" : "disabled";

    // optimistic update
    setSavingId(reminder.id);
    setRemindersDoc((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        entries: prev.entries.map((r) =>
          r.id === reminder.id ? { ...r, status: newStatus } : r
        ),
      };
    });

    try {
      await fetch(`/api/reminders/${reminder.id}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "toggle",
          status: newStatus,
        }),
      });
      // polling will reconcile if backend adjusts anything else
    } catch (err) {
      console.error("Failed to toggle reminder status", err);
      fetchReminders(); // roll back to server truth
    } finally {
      setSavingId(null);
    }
  }

  async function handleDelete(reminder) {
    if (!window.confirm(`Delete reminder: "${reminder.text}"?`)) return;

    setDeletingId(reminder.id);

    // optimistic remove
    setRemindersDoc((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        entries: prev.entries.filter((r) => r.id !== reminder.id),
      };
    });

    try {
      await fetch(`/api/memory/reminders/${reminder.id}`, {
        method: "DELETE",
      });
    } catch (err) {
      console.error("Failed to delete reminder", err);
      fetchReminders();
    } finally {
      setDeletingId(null);
    }
  }

  function formatSchedule(schedule) {
    if (!schedule) return "No schedule";
    const { minute, hour, day, dow, month, year } = schedule;
    return `m:${minute} h:${hour} d:${day} dow:${dow} mo:${month} y:${year}`;
  }

  function formatLocalDateTime(isoString) {
    if (!isoString) return null;
    const d = new Date(isoString);
    if (Number.isNaN(d.getTime())) return null;

    return d.toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  return (
    <div className="space-y-2">
      <div className="mb-3 rounded-md border border-zinc-700 bg-zinc-900/70 px-3 py-2 text-xs leading-relaxed">
        <div className="mb-1 font-semibold text-zinc-100">
          How to change reminders
        </div>
        <p className="text-zinc-200">
          You can toggle, snooze, skip, or delete reminders here.
        </p>
        <p className="mt-1 text-zinc-300">
          To change <span className="italic">when</span> a reminder fires, talk to your Muse in chat. For example:
        </p>
        <ul className="mt-1 list-disc space-y-0.5 pl-4 text-zinc-300">
          <li>“Search my reminders for ‘parking’ and show me the matches.”</li>
          <li>Then: “Change that parking reminder to weekdays at 10:45am.”</li>
        </ul>
        <p className="mt-1 text-zinc-400">
          If a reminder just fired, you can skip the search and say things like:
          “Snooze that for 15 minutes” or “Turn this into a one‑time reminder for tomorrow at 9am.”
        </p>
      </div>
      {entries.map((rem) => (
        <div
          key={rem.id}
          className="flex items-start justify-between gap-3 rounded-md border border-zinc-700 bg-zinc-900/70 px-3 py-2 text-xs"
        >
          <div className="flex flex-col gap-0.5">
            <span className="font-semibold text-zinc-100">{rem.text}</span>
          {/* <span className="text-[10px] text-muted-foreground">
              {formatSchedule(rem.schedule)}
            </span>
          */}

          {rem.cron && (
            <p className="mt-0.5 text-[11px] text-zinc-400">
              Schedule:{" "}
              <span className="font-medium">
                {cronstrue.toString(rem.cron)}
              </span>
            </p>
          )}

            <Accordion type="single" collapsible className="mt-1">
              <AccordionItem value="actions">
                <AccordionTrigger className="text-xs text-zinc-300">
                  More options
                </AccordionTrigger>
                  <AccordionContent className="pt-1 text-xs text-zinc-200">
                    <p className="mb-2">
                      Use these controls to snooze, skip, or set an end date for this reminder.
                    </p>

                    <div className="space-y-2">
                      {/* Snooze block */}
                      <div className="rounded border border-zinc-700/70 bg-zinc-900/60 p-2 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] text-zinc-400">Snooze</span>
                          {rem.snooze_until && (
                            <div className="flex items-center gap-1 text-[11px] text-zinc-400">
                              <span>
                                Until{" "}
                                <span className="font-medium">
                                  {formatLocalDateTime(rem.snooze_until)}
                                </span>
                              </span>
                              <button
                                type="button"
                                className="text-[10px] text-zinc-500 hover:text-zinc-200"
                                onClick={() => handleClearSnooze(rem)}
                              >
                                ✕
                              </button>
                            </div>
                          )}
                        </div>

                        <div className="flex flex-wrap items-center gap-1.5">
                          {[
                            { label: "5m",  m: 5,  h: 0, d: 0 },
                            { label: "15m", m: 15, h: 0, d: 0 },
                            { label: "1h",  m: 0,  h: 1, d: 0 },
                            { label: "1 day", m: 0, h: 0, d: 1 },
                          ].map((opt) => (
                            <button
                              key={opt.label}
                              type="button"
                              className="rounded border border-zinc-700 px-2 py-0.5 text-[11px] hover:bg-zinc-800"
                              onClick={() => setSnoozeFields(opt)}
                            >
                              {opt.label}
                            </button>
                          ))}
                        </div>

                        <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-zinc-300">
                          <input
                            type="number"
                            min={0}
                            max={59}
                            value={minutes}
                            onChange={(e) => setMinutes(Number(e.target.value))}
                            className="w-12 rounded border border-zinc-700 bg-zinc-900 px-1 py-0.5"
                          />
                          <span>min</span>
                          <input
                            type="number"
                            min={0}
                            max={23}
                            value={hours}
                            onChange={(e) => setHours(Number(e.target.value))}
                            className="w-12 rounded border border-zinc-700 bg-zinc-900 px-1 py-0.5"
                          />
                          <span>hr</span>
                          <input
                            type="number"
                            min={0}
                            max={365}
                            value={days}
                            onChange={(e) => setDays(Number(e.target.value))}
                            className="w-12 rounded border border-zinc-700 bg-zinc-900 px-1 py-0.5"
                          />
                          <span>day</span>

                          <button
                            type="button"
                            className="ml-auto rounded bg-purple-600 px-2 py-0.5 text-[11px] font-medium text-white hover:bg-purple-500"
                            onClick={() => handleSnooze(rem)}
                          >
                            Apply
                          </button>
                        </div>
                      </div>

                      {/* Skip block */}
                      <div className="rounded border border-zinc-700/70 bg-zinc-900/60 p-2 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] text-zinc-400">Skip until</span>
                          {rem.skip_until && (
                            <div className="flex items-center gap-1 text-[11px] text-zinc-400">
                              <span>
                                {formatLocalDateTime(rem.skip_until)}
                              </span>
                              <button
                                type="button"
                                className="text-[10px] text-zinc-500 hover:text-zinc-200"
                                onClick={() => handleClearSkip(rem)}
                              >
                                ✕
                              </button>
                            </div>
                          )}
                        </div>

                        <button
                          type="button"
                          className="rounded border border-zinc-700 px-2 py-0.5 text-[11px] hover:bg-zinc-800"
                          onClick={handleOpenSkipCal}
                        >
                          {openSkipCal ? "Cancel" : "Select date"}
                        </button>

                        {openSkipCal && (
                          <div className="mt-1 space-y-1.5">
                            <Calendar
                              mode="single"
                              selected={skipDate}
                              onSelect={setSkipDate}
                              className="rounded-md border border-zinc-700 bg-zinc-900 text-xs
                                         [&_.rdp-day]:h-7 [&_.rdp-day]:w-7
                                         [&_.rdp-day_selected]:bg-purple-600
                                         [&_.rdp-day_selected]:text-white
                                         [&_.rdp-day_selected]:font-semibold
                                         [&_.rdp-day_selected]:rounded-full"
                              captionLayout="dropdown"
                            />
                            <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-zinc-300">
                              <input
                                type="number"
                                min={0}
                                max={23}
                                value={skipHour}
                                onChange={(e) => setSkipHour(Number(e.target.value))}
                                className="w-12 rounded border border-zinc-700 bg-zinc-900 px-1 py-0.5"
                              />
                              <span>hr</span>
                              <input
                                type="number"
                                min={0}
                                max={59}
                                value={skipMinute}
                                onChange={(e) => setSkipMinute(Number(e.target.value))}
                                className="w-12 rounded border border-zinc-700 bg-zinc-900 px-1 py-0.5"
                              />
                              <span>min</span>

                              <button
                                type="button"
                                className="ml-auto rounded bg-purple-600 px-2 py-0.5 text-[11px] font-medium text-white hover:bg-purple-500"
                                onClick={() => {
                                  handleSkip(rem);
                                  setOpenSkipCal(false);
                                }}
                              >
                                Apply
                              </button>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Expiration block */}
                      <div className="rounded border border-zinc-700/70 bg-zinc-900/60 p-2 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] text-zinc-400">Expiration</span>
                          {rem.ends_on && (
                            <div className="flex items-center gap-1 text-[11px] text-zinc-400">
                              <span>
                                {formatLocalDateTime(rem.ends_on)}
                              </span>
                              <button
                                type="button"
                                className="text-[10px] text-zinc-500 hover:text-zinc-200"
                                onClick={() => handleClearExpiration(rem)}
                              >
                                ✕
                              </button>
                            </div>
                          )}
                        </div>

                        <button
                          type="button"
                          className="rounded border border-zinc-700 px-2 py-0.5 text-[11px] hover:bg-zinc-800"
                          onClick={handleOpenExprCal}
                        >
                          {openExprCal ? "Cancel" : "Select date"}
                        </button>

                        {openExprCal && (
                          <div className="mt-1 space-y-1.5">
                            <Calendar
                              mode="single"
                              selected={exprDate}
                              onSelect={setExprDate}
                              className="rounded-md border border-zinc-700 bg-zinc-900 text-xs
                                         [&_.rdp-day]:h-7 [&_.rdp-day]:w-7
                                         [&_.rdp-day_selected]:bg-purple-600
                                         [&_.rdp-day_selected]:text-white
                                         [&_.rdp-day_selected]:font-semibold
                                         [&_.rdp-day_selected]:rounded-full"
                              captionLayout="dropdown"
                            />
                            <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-zinc-300">
                              <input
                                type="number"
                                min={0}
                                max={23}
                                value={exprHour}
                                onChange={(e) => setExprHour(Number(e.target.value))}
                                className="w-12 rounded border border-zinc-700 bg-zinc-900 px-1 py-0.5"
                              />
                              <span>hr</span>
                              <input
                                type="number"
                                min={0}
                                max={59}
                                value={exprMinute}
                                onChange={(e) => setExprMinute(Number(e.target.value))}
                                className="w-12 rounded border border-zinc-700 bg-zinc-900 px-1 py-0.5"
                              />
                              <span>min</span>

                              <button
                                type="button"
                                className="ml-auto rounded bg-purple-600 px-2 py-0.5 text-[11px] font-medium text-white hover:bg-purple-500"
                                onClick={() => {
                                  handleSetExpiration(rem);
                                  setOpenExprCal(false);
                                }}
                              >
                                Apply
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </AccordionContent>
              </AccordionItem>
            </Accordion>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex flex-col items-center gap-0.5">
              <span
                className={`text-[10px] ${
                  rem.status === "disabled"
                    ? "text-neutral-400"
                    : "text-purple-300"
                }`}
              >
                {rem.status || "enabled"}
              </span>
              <button
                className={`relative inline-flex items-center w-8 h-4 rounded-full transition-colors duration-300 px-3
                  ${rem.status !== "disabled" ? "bg-purple-600" : "bg-neutral-700"}`}
                onClick={() => handleToggleStatus(rem)}
                aria-label="Enable / Disable Reminder"
                disabled={savingId === rem.id || deletingId === rem.id}
              >
                <span
                  className={`w-2 h-2 rounded-full bg-white transition-transform duration-300
                    ${rem.status !== "disabled" ? "translate-x-2" : "-translate-x-2"}`}
                />
              </button>
            </div>

            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 text-red-500 hover:text-red-600"
              onClick={() => handleDelete(rem)}
              disabled={savingId === rem.id || deletingId === rem.id}
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>

        </div>
      ))}
    </div>
  );
}