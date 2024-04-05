function createMonthSheet(year, month) {
    var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    var sheetName = year + '年' + month + '月';
    var sheet = spreadsheet.getSheetByName(sheetName);
  
    // シートが存在しない場合は新しいシートを作成
    if (!sheet) {
      sheet = spreadsheet.insertSheet(sheetName);
    } else {
      // シートが既に存在する場合は内容をクリア
      sheet.clear();
    }
  
    // ヘッダーの設定
    sheet.getRange('A7').setValue('日付');
    sheet.getRange('B7').setValue('時間');
    sheet.getRange('C7').setValue('分');
    sheet.getRange('D7').setValue('業務内容');
    sheet.getRange('E7').setValue('1週間合計（日→土曜日）');
    sheet.getRange('D4').setValue(month + '月合計稼動時間');
    sheet.getRange('E2').setValue(month + '月の給与');
  
    // 月の日付を設定
    var daysInMonth = new Date(year, month, 0).getDate();
    var values = [];
    
    for (var day = 1; day <= daysInMonth; day++) {
      var date = new Date(year, month, day);
      var formattedDate = formatDateWithJapaneseDay(date); // 日本語の曜日でフォーマット
      values.push([formattedDate, '', '', '', '']); // 日付の行に値をセット
    }
  
    // 値をスプレッドシートにセット
    var range = sheet.getRange('A8:E' + (7 + daysInMonth));
    range.setValues(values);
  
    // 週間合計のカラムに累積される稼働時間を計算するロジックを追加
    for (var i = 8; i < 8 + daysInMonth; i++) {
      var weekTotalFormula;
      if (i === 8 || new Date(year, month, i - 7).getDay() === 0) {
        weekTotalFormula = '=IF(AND(B' + i + ' <> "", C' + i + ' <> ""), B' + i + ' + C' + i + '/60, "")';
      } else {
        weekTotalFormula = '=E' + (i - 1) + '+IF(AND(B' + i + ' <> "", C' + i + ' <> ""), B' + i + ' + C' + i + '/60, "")';
      }
      sheet.getRange('E' + i).setFormula(weekTotalFormula);
    }
  
    // 月の合計稼働時間を計算する数式
    var monthlyTotalFormula = '=SUM(B8:B' + (7 + daysInMonth) + ')+SUM(C8:C' + (7 + daysInMonth) + ')/60';
    sheet.getRange('D5').setFormula(monthlyTotalFormula);
  
    // 月の給料を計算する数式（時給1500円を仮定）
    var salaryFormula = '=D5*1500';
    sheet.getRange('E3').setFormula(salaryFormula);
  
    // 1週間合計（日→土曜日）カラムの全てのセルの色をヘッダーと同じ灰色で塗りつぶす
    var weekTotalRange = sheet.getRange('E8:E' + (7 + daysInMonth));
    weekTotalRange.setBackground('#dddddd');
    
    // セルのフォーマット設定
    var headerRange = sheet.getRange('A7:E7');
    headerRange.setFontWeight('bold');
    headerRange.setBackground('#dddddd');
    sheet.setColumnWidths(1, 5, 100);
    sheet.getRange('A7:E' + (7 + daysInMonth)).setHorizontalAlignment('center');
    
    // ヘッダーの下に黒いボーダー線を追加
    headerRange.setBorder(false, false, true, false, false, false, 'black', SpreadsheetApp.BorderStyle.SOLID);
    
    // 日付と時間の間に縦の黒いボーダー線を追加
    headerRange.setBorder(null, null, null, null, true, null, 'black', SpreadsheetApp.BorderStyle.SOLID);
    
    // 日付カラムのすべてのセルに黒いボーダー線を追加
    var allDateCellsRange = sheet.getRange('A8:A' + (7 + daysInMonth));
    allDateCellsRange.setBorder(null, true, null, null, null, null, 'black', SpreadsheetApp.BorderStyle.SOLID);
    
    // 日付カラムの全てのセルにコの字型のボーダー線を追加
    var dateCellsRange = sheet.getRange('A8:A' + (7 + daysInMonth));
    dateCellsRange.setBorder(true, true, true, true, true, true, 'black', SpreadsheetApp.BorderStyle.SOLID);
  
    // 土曜日と日曜日の間にボーダー線を引く
    setWeekendBorders(sheet, year, month, daysInMonth);
  }
  
  function formatDateWithJapaneseDay(date) {
    var dayNames = ['日', '月', '火', '水', '木', '金', '土'];
    var dayName = dayNames[date.getDay()];
    return Utilities.formatDate(date, Session.getScriptTimeZone(), "yyyy年MM月dd日") + dayName + '曜日';
  }
  
  function setWeekendBorders(sheet, year, month, daysInMonth) {
    // 土曜日の日付を探して、その行にボーダーを設定する
    for (var row = 8; row < 8 + daysInMonth; row++) {
      var date = new Date(year, month, row - 7);
      if (date.getDay() === 6) { // 土曜日の場合
        var range = sheet.getRange('A' + row + ':E' + row);
        range.setBorder(null, null, true, null, null, null, 'black', SpreadsheetApp.BorderStyle.SOLID);
      }
    }
  }