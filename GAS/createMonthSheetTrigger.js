function createMonthlyTrigger() {
    // トリガーを設定する前に、既存のトリガーをクリア
    var triggers = ScriptApp.getProjectTriggers();
    for (var i = 0; i < triggers.length; i++) {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  
    // 毎月1日に実行するトリガーを設定
    ScriptApp.newTrigger('autoCreateMonthlySheet')
        .timeBased()
        .onMonthDay(1)
        .atHour(0)
        .create();
  }
  
  function autoCreateMonthlySheet() {
    var today = new Date();
    var year = today.getFullYear();
    var month = today.getMonth() + 1; // 月は0から始まる　// *ここがおかしい031月みたいな表記になっている*
  
    if (month < 10) {
      month = "0" + month;
    }
  
    createMonthSheet(year, month);
  }