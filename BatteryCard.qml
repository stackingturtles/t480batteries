import QtQuick
import qs.Commons
import qs.Ui
import "Model.js" as Model

Column {
  id: card
  required property var battery
  required property color foreground
  required property string fontFamily
  property bool panelOpen: false
  spacing: Style.space(10)

  Item {
    width: parent.width
    implicitHeight: Math.max(labels.implicitHeight, percentage.implicitHeight)

    Text {
      id: icon
      anchors.left: parent.left
      anchors.verticalCenter: parent.verticalCenter
      text: Model.icon(card.battery)
      textFormat: Text.PlainText
      color: card.foreground
      opacity: card.battery.present ? 1 : 0.5
      font.family: card.fontFamily
      font.pixelSize: Style.font.display
    }

    Column {
      id: labels
      anchors.left: icon.right
      anchors.leftMargin: Style.space(14)
      anchors.right: percentage.left
      anchors.rightMargin: Style.space(10)
      anchors.verticalCenter: parent.verticalCenter
      spacing: Style.space(2)
      Text {
        width: parent.width
        text: card.battery.label + " · " + card.battery.id
        textFormat: Text.PlainText
        color: card.foreground
        font.family: card.fontFamily
        font.pixelSize: Style.font.title
        font.bold: true
        elide: Text.ElideRight
      }
      Text {
        width: parent.width
        text: Model.status(card.battery).toUpperCase()
        textFormat: Text.PlainText
        color: card.foreground
        opacity: 0.6
        font.family: card.fontFamily
        font.pixelSize: Style.font.caption
        font.bold: true
        font.letterSpacing: 0.6
        elide: Text.ElideRight
      }
    }

    Text {
      id: percentage
      anchors.right: parent.right
      anchors.verticalCenter: parent.verticalCenter
      text: Model.percent(card.battery.percentage)
      textFormat: Text.PlainText
      color: card.foreground
      font.family: card.fontFamily
      font.pixelSize: Style.font.displayLarge
      font.bold: true
    }
  }

  Rectangle {
    id: track
    width: parent.width
    height: Style.space(8)
    radius: height / 2
    color: Qt.rgba(card.foreground.r, card.foreground.g, card.foreground.b, 0.12)
    Rectangle {
      width: track.width * Model.fraction(card.battery.percentage)
      height: track.height
      radius: track.radius
      color: card.foreground
      Behavior on width { NumberAnimation { duration: 320; easing.type: Easing.OutCubic } }
      SequentialAnimation on opacity {
        running: card.panelOpen && card.battery.state === "charging"
        loops: Animation.Infinite
        alwaysRunToEnd: true
        NumberAnimation { from: 1; to: 0.55; duration: 950; easing.type: Easing.InOutSine }
        NumberAnimation { from: 0.55; to: 1; duration: 950; easing.type: Easing.InOutSine }
      }
    }
  }

  Row {
    width: parent.width
    visible: card.battery.present
    spacing: Style.space(20)
    Column {
      width: (parent.width - parent.spacing) / 2
      spacing: Style.spacing.labelGap
      InfoPair { label: "Battery size"; value: Model.quantity(card.battery.fullWh, "Wh") }
      InfoPair { label: "Charge limit"; value: Model.percent(card.battery.thresholdEnd) }
      InfoPair { label: "Charge cycles"; value: Model.known(card.battery.cycles) ? String(card.battery.cycles) : "—" }
    }
    Column {
      width: (parent.width - parent.spacing) / 2
      spacing: Style.spacing.labelGap
      InfoPair {
        label: card.battery.state === "holding" ? "Charge limit" : card.battery.state === "charging" ? (card.battery.thresholdEnd < 100 ? "Time to limit" : "Time to full") : "Time left"
        value: card.battery.state === "holding" ? Model.threshold(card.battery) : Model.duration(card.battery.seconds, card.battery.estimated)
      }
      InfoPair {
        label: card.battery.state === "charging" ? "Charging" : card.battery.state === "discharging" ? "Discharging" : "Power flow"
        value: Model.quantity(card.battery.rateW, "W")
      }
    }
  }

  component InfoPair: Row {
    property string label: ""
    property string value: ""
    width: parent.width
    spacing: Style.space(6)
    Text {
      text: parent.label
      color: card.foreground
      opacity: 0.6
      font.family: card.fontFamily
      font.pixelSize: Style.font.bodySmall
      textFormat: Text.PlainText
    }
    Item { width: Math.max(0, parent.width - parent.children[0].implicitWidth - parent.children[2].implicitWidth - parent.spacing * 2); height: 1 }
    Text {
      text: parent.value
      color: card.foreground
      font.family: card.fontFamily
      font.pixelSize: Style.font.bodySmall
      textFormat: Text.PlainText
    }
  }
}
