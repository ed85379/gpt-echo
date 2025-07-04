"use client";
import React from "react";
import { Remarkable } from 'remarkable';
import { linkify } from 'remarkable/linkify';
import MessageActions from "./MessageActions";
import { CandleHolderLit } from "../utils/messageActions";
import { BookMarked, EyeOff, Shredder } from "lucide-react";

const md = new Remarkable({
  html: false,
  breaks: true,
  linkTarget: "_blank",
  typographer: true,
});
md.use(linkify);

const formatTimestamp = (utcString) => {
  if (!utcString) return "";
  const dt = new Date(utcString);
  return dt.toLocaleString();
};

const MessageItem = React.forwardRef(function MessageItem({
  msg,
  projects,
  projectsLoading,
  projectMap,
  onSetProject,
  onClearProject,
  onAddTag,
  onRemoveTag,
  onTogglePrivate,
  onToggleRemembered,
  onDelete,
  tagDialogOpen,
  setTagDialogOpen,
  projectDialogOpen,
  setProjectDialogOpen,
  museName,
}, ref) {
  if (!msg) return <div>[No message]</div>;
  let renderedHTML = "";
  try {
    renderedHTML = md.render((msg.message || msg.text || "").trim());
  } catch (e) {
    renderedHTML = "<em>[Failed to render markdown]</em>";
    console.error("Remarkable error:", e, msg.message || msg.text);
  }

  const effectiveRole = msg.from || msg.role || "";
  let displayName = "Other";
  let bubbleClass = "bg-purple-900 text-white self-start text-left";
  if (effectiveRole === "user") {
    displayName = "You";
    bubbleClass = "bg-neutral-800 text-purple-100 self-end text-left";
  } else if (effectiveRole === "muse" || effectiveRole === "iris") {
    displayName = museName;
    bubbleClass = "bg-purple-950 text-white self-start text-left";
  } else if (effectiveRole === "other" || effectiveRole === "friend") {
    displayName = msg.username ? msg.username : "Friend";
    bubbleClass = "bg-neutral-700 text-white self-start text-left";
  } else if (effectiveRole) {
    displayName = effectiveRole.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
    bubbleClass = "bg-purple-900 text-white self-start text-left";
  }

  const rightAlign = effectiveRole === "user";
  const isPrivate = !!msg.is_private;
  const isRemembered = !!msg.remembered;
  const isDeleted = !!msg.is_deleted;
  const inProject = msg.project_id;
  const userTags = msg.user_tags?.filter(t => t !== "private" && t !== "deleted" && t !== "remembered") || [];
  const bubbleWidth = "max-w-[80%]";

  return (
    <div ref={ref} className={`space-y-1 flex flex-col ${rightAlign ? "items-end" : "items-start"}`}>
      <div className={`${bubbleWidth} ${rightAlign ? "ml-auto" : ""}`}>
        <div className="text-xs text-neutral-400">{displayName}</div>
        <div className="text-xs text-neutral-500">{formatTimestamp(msg.timestamp)}</div>
        <div className={`relative group text-sm px-3 py-2 rounded-lg whitespace-pre-wrap ${bubbleClass}`}>
          <div
            className="prose prose-invert max-w-none"
            dangerouslySetInnerHTML={{ __html: renderedHTML }}
          />
          <MessageActions
            msg={msg}
            projects={projects}
            projectsLoading={projectsLoading}
            projectMap={projectMap}
            onSetProject={onSetProject}
            onClearProject={onClearProject}
            onAddTag={onAddTag}
            onRemoveTag={onRemoveTag}
            onTogglePrivate={onTogglePrivate}
            onToggleRemembered={onToggleRemembered}
            onDelete={onDelete}
            tagDialogOpen={tagDialogOpen}
            setTagDialogOpen={setTagDialogOpen}
            projectDialogOpen={projectDialogOpen}
            setProjectDialogOpen={setProjectDialogOpen}
          />
        </div>
        <div className="flex flex-wrap gap-1 mt-1 ml-2">
          {inProject && projectMap[inProject] && (
            <span className="bg-purple-800 text-xs text-purple-100 px-2 py-0.5 rounded-full flex items-center gap-1">
              <BookMarked size={14} className="inline" />
              <span className="font-semibold">{projectMap[inProject].name || "Project"}</span>
            </span>
          )}
          {userTags.map(tag => (
            <span key={tag} className="bg-purple-800 text-xs text-purple-100 px-2 py-0.5 rounded-full">
              #{tag}
            </span>
          ))}
          {isRemembered && (
            <span className="bg-neutral-700 text-xs text-purple-300 px-2 py-0.5 rounded-full flex items-center gap-1">
              <CandleHolderLit size={14} className="inline" /> Remembered
            </span>
          )}
          {isPrivate && (
            <span className="bg-neutral-700 text-xs text-purple-300 px-2 py-0.5 rounded-full flex items-center gap-1">
              <EyeOff size={14} className="inline" /> Private
            </span>
          )}
          {isDeleted && (
            <span className="bg-neutral-700 text-xs text-purple-300 px-2 py-0.5 rounded-full flex items-center gap-1">
              <Shredder size={14} className="inline" /> Recycled
            </span>
          )}
        </div>
      </div>
    </div>
  );
});

export default MessageItem;