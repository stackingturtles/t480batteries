function clampIndex(index, length) {
  if (length <= 0) return 0
  return Math.max(0, Math.min(length - 1, index))
}

function selectProfileIndex(index, delta, profiles) {
  var values = Array.isArray(profiles) ? profiles : []
  if (values.length === 0) return 0
  return clampIndex(index + delta, values.length)
}

function parseKeyValue(raw) {
  var next = {}
  var lines = String(raw || "").split("\n")
  for (var i = 0; i < lines.length; i++) {
    var idx = lines[i].indexOf("\t")
    if (idx <= 0) continue
    next[lines[i].substring(0, idx)] = lines[i].substring(idx + 1).trim()
  }
  return next
}

function parseProfiles(raw, previousIndex) {
  var lines = String(raw || "").split("\n")
  var list = []
  var active = ""
  for (var i = 0; i < lines.length; i++) {
    var line = lines[i].trim()
    if (!line) continue
    var parts = line.split("\t")
    list.push(parts[0])
    if (parts[1] === "1") active = parts[0]
  }
  return {
    profiles: list,
    activeProfile: active,
    profileIndex: clampIndex(previousIndex || 0, list.length)
  }
}

function profileIcon(name) {
  if (name === "power-saver") return "󰌪"
  if (name === "balanced") return "󰊚"
  if (name === "performance") return "󰓅"
  return "󰂄"
}

function known(value) { return typeof value === "number" && isFinite(value) }
function percent(value) { return known(value) ? Math.round(value) + "%" : "—" }
function quantity(value, suffix) {
  return known(value) ? (Math.round(value * 10) / 10) + suffix : "—"
}
function fraction(value) { return known(value) ? Math.max(0, Math.min(1, value / 100)) : 0 }

function icon(battery) {
  var b = battery || {}
  if (b.state === "absent" || !known(b.percentage)) return "󰂑"
  var plain = ["󰁺", "󰁻", "󰁼", "󰁽", "󰁾", "󰁿", "󰂀", "󰂁", "󰂂", "󰁹"]
  var charging = ["󰢜", "󰂆", "󰂇", "󰂈", "󰢝", "󰂉", "󰢞", "󰂊", "󰂋", "󰂅"]
  var index = Math.max(0, Math.min(9, Math.floor(b.percentage / 10)))
  return (b.state === "charging" ? charging : plain)[index]
}

function status(battery) {
  return ({absent: "Not detected", charging: "Charging", discharging: "Discharging",
           full: "Fully charged", standby: "Standby", holding: "Holding at charge limit",
           unknown: "State unavailable"})[(battery || {}).state] || "State unavailable"
}

function duration(seconds, estimated) {
  if (!known(seconds) || seconds <= 0) return "—"
  var minutes = Math.floor(seconds / 60)
  var hours = Math.floor(minutes / 60)
  var text = minutes < 1 ? "<1m" : (hours ? hours + "h" + (minutes % 60 ? " " + minutes % 60 + "m" : "") : minutes + "m")
  return (estimated ? "~" : "") + text
}

function threshold(b) {
  if (!known(b.thresholdEnd)) return "—"
  return known(b.thresholdStart) && b.thresholdStart !== b.thresholdEnd
    ? b.thresholdStart + "–" + b.thresholdEnd + "%" : b.thresholdEnd + "%"
}

function emptyBattery(id, label) { return {id: id, label: label, present: false, state: "absent"} }

if (typeof module !== "undefined") {
  module.exports = {known, percent, quantity, fraction, icon, status, duration, threshold,
                   parseKeyValue, parseProfiles, selectProfileIndex, profileIcon}
}

function saverState(snapshot) {
  var packs = (snapshot.batteries || []).filter(function(b) { return b.present })
  var supported = packs.length > 0 && packs.every(function(b) { return known(b.thresholdStart) && known(b.thresholdEnd) })
  var enabled = supported && packs.every(function(b) { return b.thresholdEnd === 80 && b.thresholdStart === 75 })
  var off = supported && packs.every(function(b) { return b.thresholdEnd === 100 && b.thresholdStart === 0 })
  return {enabled: enabled, available: supported && snapshot.chargeControlInstalled === true,
    description: !snapshot.chargeControlInstalled ? "Install charge control to enable this feature."
      : !supported ? "Charge control unavailable for detected batteries."
      : enabled ? "80% limit · charging restarts below 75%"
      : off ? "Off · batteries may charge to 100%"
      : "Custom or mixed limits · enable to set both to 80%"}
}
if (typeof module !== "undefined") module.exports.saverState = saverState
