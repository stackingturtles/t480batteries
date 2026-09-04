import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.UPower
import qs.Commons
import qs.Ui
import "Model.js" as Model

// Derived from Omarchy's Power panel; clonedFrom preserves its IPC shortcuts.
Panel {
  id: root
  moduleName: "omarchy.power"
  ipcTarget: "omarchy.power"
  manageIpc: false
  property var snapshot: ({batteries: [Model.emptyBattery("BAT0", "Internal"), Model.emptyBattery("BAT1", "External")], state: "absent"})
  property string telemetryError: ""
  property string saverError: ""
  property bool saverCursor: false
  readonly property var saverState: Model.saverState(snapshot)
  function toggleSaver() {
    if (saverProc.running || !saverState.available) return
    saverError = ""
    saverProc.command = ["pkexec", "/usr/local/libexec/t480batteries/charge_limit.py", saverState.enabled ? "disable" : "enable"]
    saverProc.running = true
  }
  property var profiles: []
  property string activeProfile: ""
  property int profileIndex: 0
  property bool cursorActive: false
  readonly property bool showPercentage: setting("showPercentage", false) === true
  readonly property bool discharging: snapshot.acOnline === null || snapshot.acOnline === undefined ? UPower.onBattery : !snapshot.acOnline
  readonly property real openPanelIndicatorWidth: showPercentage && !button.vertical ? button.glyphPaintedWidth : 0
  readonly property string readerPath: decodeURIComponent(Qt.resolvedUrl("batteries.py").toString().replace(/^file:\/\//, ""))

  function refreshBatteries() {
    if (!batteryProc.running) batteryProc.running = true
  }
  function refresh() {
    refreshBatteries()
    if (!profilesProc.running) profilesProc.running = true
  }
  function readSnapshot(raw) {
    try {
      var next = JSON.parse(raw)
      if (next.schemaVersion !== 1 || !Array.isArray(next.batteries) || next.batteries.length !== 2)
        throw new Error("Invalid battery snapshot")
      snapshot = next
      telemetryError = ""
    } catch (error) {
      telemetryError = "Battery readings unavailable · retrying"
      snapshot = {batteries: [Model.emptyBattery("BAT0", "Internal"), Model.emptyBattery("BAT1", "External")], state: "absent"}
    }
  }
  function updateProfiles(raw) {
    var parsed = Model.parseProfiles(raw, profileIndex)
    if (parsed.profiles.length === 0) return
    profiles = parsed.profiles
    activeProfile = parsed.activeProfile
    profileIndex = parsed.profileIndex
    if (opened && !cursorActive) {
      var idx = profiles.indexOf(activeProfile)
      if (idx >= 0) profileIndex = idx
    }
  }
  function profileIcon(name) { return Model.profileIcon(name) }
  function selectProfileByDelta(delta) { profileIndex = Model.selectProfileIndex(profileIndex, delta, profiles) }
  function activateSelectedProfile() {
    if (profileIndex >= 0 && profileIndex < profiles.length) setProfile(profiles[profileIndex])
  }
  function setProfile(profile) {
    if (profiles.indexOf(profile) < 0 || actionProc.running) return
    actionProc.command = ["omarchy-powerprofiles-set", root.discharging ? "battery" : "ac", profile]
    actionProc.running = true
  }
  function togglePercentage() {
    root.settings = Object.assign({}, root.settings, { showPercentage: !root.showPercentage })
    if (root.bar && root.bar.shell) root.bar.shell.updateEntryInline(root.moduleName, root.settings)
  }
  IpcHandler {
    target: "omarchy.power"
    function open() { root.open() }
    function close() { root.close() }
    function show() { root.open() }
    function hide() { root.close() }
    function toggle() { root.toggle() }
    function togglePercentage() { root.togglePercentage() }
  }
  onOpenedChanged: {
    if (opened) {
      refresh()
      var idx = profiles.indexOf(activeProfile)
      profileIndex = idx >= 0 ? idx : 0
      cursorActive = false
    }
  }
  Component.onCompleted: refreshBatteries()
  Process {
    id: batteryProc
    command: ["python3", root.readerPath]
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.readSnapshot(text) }
    onExited: function(code, status) { if (code !== 0) root.readSnapshot("") }
  }
  Process {
    id: profilesProc
    command: ["omarchy-powerprofiles-list", "--active-state"]
    stdout: StdioCollector { waitForEnd: true; onStreamFinished: root.updateProfiles(text) }
  }
  Process {
    id: saverProc
    onExited: function(code, status) {
      root.saverError = code === 0 ? "" : code === 126 ? "Change cancelled." : "Could not change limits. Authenticate and try again."
      root.refreshBatteries()
    }
  }
  Process { id: actionProc; onExited: root.refresh() }
  Timer {
    interval: root.opened ? 5000 : 30000
    running: true
    repeat: true
    onTriggered: { if (root.opened) root.refresh(); else root.refreshBatteries() }
  }
  Connections {
    target: UPower
    function onOnBatteryChanged() { root.refresh() }
  }
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight
  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: root.showPercentage && !vertical
      ? Model.percent(root.snapshot.percentage) + " " + Model.icon(root.snapshot)
      : Model.icon(root.snapshot)
    slotSize: Style.bar.iconSlot * (root.showPercentage && !vertical ? 2 : 1)
    tooltipText: ""
    onPressed: function(b) { if (b === Qt.RightButton) root.togglePercentage(); else root.toggle() }
  }
  KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(440))
    contentHeight: panel.fittedContentHeight(column.implicitHeight)
    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onMoveRequested: function(dx, dy) {
        if (!root.cursorActive) { root.cursorActive = true; return }
        if (dy !== 0) root.saverCursor = dy < 0
        else if (!root.saverCursor) root.selectProfileByDelta(dx)
      }
      onActivateRequested: if (root.cursorActive) { if (root.saverCursor) root.toggleSaver(); else root.activateSelectedProfile() }
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }
      Flickable {
        anchors.fill: parent
        contentHeight: column.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.VerticalFlick
        Column {
          id: column
          width: parent.width
          spacing: Style.space(16)
          Row {
            width: parent.width
            Text {
              text: "T480 BATTERIES"
              color: root.bar.foreground
              font.family: root.bar.fontFamily
              font.pixelSize: Style.font.caption
              font.bold: true
              font.letterSpacing: 1
            }
            Item { width: Math.max(0, parent.width - parent.children[0].implicitWidth - parent.children[2].implicitWidth); height: 1 }
            Text {
              text: "Combined " + Model.percent(root.snapshot.percentage)
              color: root.bar.foreground
              opacity: 0.6
              font.family: root.bar.fontFamily
              font.pixelSize: Style.font.caption
            }
          }
          Text {
            visible: root.telemetryError !== ""
            width: parent.width
            text: root.telemetryError
            color: root.bar.foreground
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.caption
            wrapMode: Text.Wrap
          }
          BatteryCard {
            width: parent.width
            battery: root.snapshot.batteries[0]
            foreground: root.bar.foreground
            fontFamily: root.bar.fontFamily
            panelOpen: root.opened
          }
          PanelSeparator { foreground: root.bar.foreground }
          BatteryCard {
            width: parent.width
            battery: root.snapshot.batteries[1]
            foreground: root.bar.foreground
            fontFamily: root.bar.fontFamily
            panelOpen: root.opened
          }
          Text {
            width: parent.width
            text: "~ Times are estimates for each active battery."
            color: root.bar.foreground
            opacity: 0.5
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.caption
          }
        PanelSeparator { foreground: root.bar.foreground }
          Toggle {
            width: parent.width
            label: "Battery lifespan saver"
            description: saverProc.running ? "Applying · authentication may be required…" : root.saverState.description
            checked: root.saverState.enabled
            enabled: root.saverState.available && !saverProc.running
            opacity: enabled ? 1 : 0.6
            hasCursor: root.cursorActive && root.saverCursor
            foreground: root.bar.foreground
            fontFamily: root.bar.fontFamily
            onClicked: root.toggleSaver()
            onHovered: function(h) { if (h) { root.cursorActive = true; root.saverCursor = true } }
          }
          Text {
            visible: root.saverError !== ""
            width: parent.width
            text: root.saverError
            wrapMode: Text.Wrap
            color: root.bar.foreground
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.caption
          }
        // ---------- Power profile picker ----------
        PanelSeparator {
          foreground: root.bar.foreground
        }

        Column {
          width: parent.width
          spacing: Style.space(10)

          PanelSectionHeader {
            text: "POWER PROFILE"
            foreground: root.bar.foreground
            fontFamily: root.bar.fontFamily
          }

          Row {
            id: profileRow
            width: parent.width
            spacing: Style.space(6)

            readonly property real cellWidth: root.profiles.length > 0
              ? (width - spacing * (root.profiles.length - 1)) / root.profiles.length
              : 0

            Repeater {
              model: root.profiles
              Button {
                required property var modelData
                required property int index
                width: profileRow.cellWidth
                iconText: root.profileIcon(String(modelData))
                iconSize: Style.font.title
                text: String(modelData).charAt(0).toUpperCase() + String(modelData).slice(1)
                fontSize: Style.font.bodySmall
                foreground: root.bar.foreground
                fontFamily: root.bar.fontFamily
                horizontalPadding: Style.spacing.controlPaddingX
                verticalPadding: Style.spacing.controlPaddingY + Style.space(2)
                bordered: true
                active: root.activeProfile === modelData
                hasCursor: root.cursorActive && !root.saverCursor && root.profileIndex === index
                onClicked: root.setProfile(modelData)
                onHovered: function(h) {
                  if (h) {
                    root.cursorActive = true
                    root.saverCursor = false
                    root.profileIndex = index
                  }
                }
              }
            }
          }
        }
        }
      }
    }
  }
}
