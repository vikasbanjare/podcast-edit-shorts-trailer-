# Premiere Pro MCP tool map (checked 28 Oct 2026)

There is no official Adobe Premiere MCP. Adobe's "Adobe for creativity" connector covers Express, Firefly and
Acrobat, and its video tools are cloud tools that can't drive the Premiere desktop app. The servers below are
community projects. Their tool names were read from each repository's tool-definition source. `?` means not
verified. **Always fetch the live schema before calling**, because these projects change weekly.

## Identify the server

| Server | Telltale tools | Bridge | Notes |
|---|---|---|---|
| **A** [hetpatel-11/Adobe_Premiere_Pro_MCP](https://github.com/hetpatel-11/Adobe_Premiere_Pro_MCP) (npm `adobe-premiere-pro-mcp`) | only `search_tools`, `get_tool_schema`, `invoke_tool`, `verify_premiere_connection`, `list_sequences` visible | CEP + ExtendScript/QE | All other tools go through `invoke_tool {name, args}` unless the server runs with `PREMIERE_MCP_TOOLSET=full`. camelCase params. |
| **B** [leancoderkavy/premiere-pro-mcp](https://github.com/leancoderkavy/premiere-pro-mcp) (npm `premiere-pro-mcp`) | `set_item_in_out`, `overwrite_clip`, `ripple_remove_timeline_ranges`, `*_uxp` | CEP (+ optional UXP) | snake_case params (`item_id`, `node_id`, `*_seconds`). Most `sequence_id` params accept a name or an ID. |
| **C** [ayushozha/AdobePremiereProMCP](https://github.com/ayushozha/AdobePremiereProMCP) | everything prefixed `premiere_` | Go → gRPC → CEP | Uses index-based params (`sequence_index`, `track_index`). |
| **D** [antipaster/Adobe-Premiere-Pro-MCP](https://github.com/antipaster/Adobe-Premiere-Pro-MCP) | `clone_sequence{sequenceName}`, `add_tiktok_caption` | CEP over WebSocket :8097 | Windows only. |
| **E** [CaYatur/PremiereProMCP](https://github.com/CaYatur/PremiereProMCP) | `sequence_find_by_name`, `clip_overwrite`, `tool_search`/`tool_invoke` | UXP over WebSocket :8265 | Premiere 26+. Times are **tick strings**. No native razor (emulated). |
| **F** [nepfaff/premiere-pro-mcp](https://github.com/nepfaff/premiere-pro-mcp) | single `execute-script` | UXP | Use the UXP API directly (see bottom). |

If the user's server isn't listed, map by description and confirm each schema. Then use the generic operations below.

## Generic operations → tool names

| Operation | A | B | C | D | E |
|---|---|---|---|---|---|
| Connection check | `verify_premiere_connection` | `list_sequences` | `premiere_get_sequence_list` | `get_sequences` | `sequence_list` |
| List sequences / find by name | `list_sequences` → match `name` | `list_sequences` (or pass the name as `sequence_id`) | `premiere_get_sequence_list` | `get_sequences` | `sequence_find_by_name{query}` |
| Set active | `set_active_sequence{sequenceId}` | `set_active_sequence` | `premiere_set_active_sequence` | `set_active_sequence` | `sequence_set_active` |
| New sequence | `create_sequence{name,presetPath}` | `create_sequence_from_preset{name,preset_path}` | `premiere_create_sequence{name,width,height,frame_rate,…}` | `create_sequence` | `sequence_create{name,presetPath?,width?,height?,frameRate?}` |
| Duplicate sequence | `duplicate_sequence{sequenceId,newName,clearContents?}` | `duplicate_sequence{sequence_id}` | `premiere_duplicate_sequence{sequence_index}` | `clone_sequence{sequenceName,newName}` | none found |
| Frame size 1080x1920 | `set_sequence_settings{sequenceId,settings:{width,height}}` | `set_sequence_resolution` / `set_sequence_settings` | `premiere_create_vertical_version` | ? | `sequence_create` width/height |
| **Place a range** | `add_to_timeline{sequenceId,projectItemId,trackIndex,time,sourceInPoint,sourceOutPoint,insertMode?,linkAudio?}` | `set_item_in_out{item_id,in_seconds,out_seconds}` then `overwrite_clip{item_id,start_seconds,track_index,audio_track_index}` | `premiere_overwrite_clip{project_item_index,time,video_track_index,audio_track_index}` (set in/out first; `premiere_place_clip` out-point param ?) | `overwrite_clip_to_timeline{projectItemId,trackIndex,startTime,inPoint?,outPoint?}` | set source in/out, then `clip_overwrite{sequenceId,trackType,trackIndex,projectItemId,atTicks}` |
| **Place many (batch)** | `add_to_timeline_batch{sequenceId,clips:[{projectItemId,trackIndex,time,sourceInPoint,sourceOutPoint,linkAudio}]}` | `add_markers_batch` only (no clip batch found) | – | – | – |
| Read back clips | `list_sequence_tracks{sequenceId}` (start/end only, no source in-point or media path) | `list_sequence_tracks` | ? | ? | ? |
| Add tracks | `add_track` | `add_track` | ? | ? | ? |
| Mute an audio track | `mute_track{sequenceId,trackIndex,muted}` | `mute_track` | ? | ? | ? |
| Video without linked audio | `add_to_timeline(_batch)` with `linkAudio:false` | fetch schema; else remove the linked audio clip after placing | ? | ? | ? |
| Razor | `razor_timeline_at_time{sequenceId?,time,videoTrackIndices?,audioTrackIndices?}` | `razor_all_tracks{time_seconds,track_type}` | `premiere_razor_clip{track_type,track_index,time}` | `razor_all_tracks` | `clip_split{…,atTicks}` (emulated) |
| Ripple delete | `remove_from_timeline{clipId,sequenceId?,deleteMode:'ripple'}` | `ripple_remove_timeline_ranges{ranges,dry_run}` → apply with token | `premiere_ripple_delete_gap` | `ripple_delete` | `clip_ripple_delete` |
| Markers | `add_marker{sequenceId,time,name,comment?}` | `add_markers_batch{sequence_id,markers[]}` | `premiere_add_sequence_marker{time,name,comment,color}` | `add_marker` | `markers_add_many` |
| Scale / position | `set_clip_properties{clipId,properties:{scale,position:{x,y}}}` (+ `_batch`) | `set_clip_scale{node_id,scale}` | `premiere_set_scale`, `premiere_set_position` | `set_effect_property` | `clip_set_transform{x,y,scale}` |
| Auto Reframe | `auto_reframe_sequence{sequenceId,numerator:9,denominator:16,newName?}` | `auto_reframe_sequence{sequence_id,target_width,target_height,new_name}` | `premiere_auto_reframe` | – | – |
| Captions from SRT | `create_caption_track{sequenceId,projectItemId}` | `create_caption_track` | `premiere_add_subtitles_from_srt` | `add_caption_sequence` | `caption_place_from_srt` |
| Sequence in/out | `set_sequence_in_out_points{sequenceId,inPoint,outPoint}` | `set_sequence_in_out_points` | – | – | `sequence_set_in_out{sequenceId,inTicks,outTicks}` |
| Export (approval only) | `export_sequence{sequenceId,outputPath,presetPath,sourceRange}` (queues to AME) | `export_sequence{output_path,preset_path?,range,timeout_minutes}` (waits, checks duration) | `premiere_export` | `export_sequence{outputPath,presetPath,useInOut?}` | `export_sequence{sequenceId,outputPath,presetPath}` |
| Raw script | `execute_extendscript{script}` | `execute_extendscript{code}` (must `return __result({...})`) | `premiere_execute_extendscript` (hidden unless the `unsafe` profile is on) | `execute_extendscript{script}` | – |

## Time units

- A, B, C, D: **seconds** (float) → send the plan's `*_s` values.
- E: **ticks as strings** → send `*_ticks` as a string. 254,016,000,000 ticks = 1 second.
- QE `razor()`: **timecode string** `HH:MM:SS:FF` → send `*_tc`. Some servers build timecode from the
  timebase themselves and can be a frame off on 23.976/29.97. Read back after cutting.

## Known pitfalls

- A: `Sequence.clone()` returns a ProjectItem. Resolve the new sequence by name afterwards.
- QE track indices count gaps and transitions, so they don't equal DOM clip indices. Prefer placement over razor.
- B: `add_to_timeline` ripple-inserts. Use `overwrite_clip` for placement. `ripple_remove_timeline_ranges` works on
  the active sequence only and needs a dry run first.
- B: Auto Reframe of a 1080p source yields 607x1080 before the server rescales. Check the final frame size.
- Placing a range by setting in/out on the source project item leaves those marks on the item. Clear them after.
- Titles and text overlays generally need a `.mogrt`. Captions can't be read back.
- All servers need Premiere open with the panel running (CEP servers also need CEP debug mode enabled).
- Adobe has scheduled CEP's retirement: no new submissions from Dec 2027, off by default from Dec 2028, removed
  Dec 2029. ExtendScript has no removal date. UXP servers (E, F) are the long-term path.

## Read the source layout (read-only)

Track listings from the servers don't include each clip's source in-point or media path, and the cut plan needs
both. Run this through the raw-script tool (server B: wrap the return as `return __result(...)`) and save the
JSON output as `layout.json`. It only reads. Untested against a live Premiere build, so check that the output
lists every camera and mic.

```javascript
(function () {
  var name = "SOURCE_SEQUENCE_NAME";
  var seq = null;
  for (var i = 0; i < app.project.sequences.numSequences; i++) {
    if (app.project.sequences[i].name === name) { seq = app.project.sequences[i]; break; }
  }
  if (!seq) return JSON.stringify({error: "sequence not found: " + name});
  function tracks(list) {
    var out = [];
    for (var t = 0; t < list.numTracks; t++) {
      var tr = list[t], clips = [];
      for (var c = 0; c < tr.clips.numItems; c++) {
        var cl = tr.clips[c], pi = cl.projectItem;
        clips.push({name: cl.name, start: cl.start.seconds, end: cl.end.seconds,
                    "in": cl.inPoint.seconds, out: cl.outPoint.seconds,
                    project_item_id: pi ? pi.nodeId : null,
                    media_path: pi && pi.getMediaPath ? pi.getMediaPath() : null});
      }
      out.push({index: t, name: tr.name, muted: tr.isMuted ? tr.isMuted() : false, clips: clips});
    }
    return out;
  }
  return JSON.stringify({sequence: {name: seq.name, id: seq.sequenceID,
                                    frame_ticks: seq.timebase, width: seq.frameSizeHorizontal,
                                    height: seq.frameSizeVertical},
                         video_tracks: tracks(seq.videoTracks), audio_tracks: tracks(seq.audioTracks)});
})();
```

Frame rate = 254016000000 / `frame_ticks` (e.g. 10160640000 → 25 fps). A multicam source clip appears as one
project item per track; that's fine, because it is placed the same way.

## ExtendScript fallback (raw-script tools only)

Use this only when a needed operation has no tool. Untested against a live Premiere build, so run it on one
sequence and read the result back before looping. Values come from the plan.

```javascript
// Place one segment of the source sequence (nested) into a target sequence, by name.
function findSeq(name) {
  for (var i = 0; i < app.project.sequences.numSequences; i++) {
    if (app.project.sequences[i].name === name) return app.project.sequences[i];
  }
  return null;
}
var src = findSeq("SOURCE_SEQUENCE_NAME");          // plan.source_sequence
var dst = findSeq("EP12_SHORT_01_why-i-quit");      // plan.sequences[i].name (created beforehand)
var item = src.projectItem;
item.setInPoint(SRC_IN_SECONDS, 4);                   // segment.src_in_s, 4 = all media types
item.setOutPoint(SRC_OUT_SECONDS, 4);                 // segment.src_out_s
dst.videoTracks[0].overwriteClip(item, TIMELINE_IN_SECONDS);  // segment.timeline_in_s
item.clearInPoint(); item.clearOutPoint();            // remove the side-effect marks
var c = dst.videoTracks[0].clips[dst.videoTracks[0].clips.numItems - 1];
JSON.stringify({start: c.start.seconds, end: c.end.seconds, inPoint: c.inPoint.seconds, outPoint: c.outPoint.seconds});
```

UXP (servers E/F, Premiere 25.6+): wrap edits in `project.lockedAccess(() => project.executeTransaction(cb))`, and
use `SequenceEditor.createOverwriteItemAction`, `createSetInPointAction`/`createSetOutPointAction` and
`createAddMarkerAction`, with times from `TickTime.createWithSeconds(...)`.
