document.addEventListener("DOMContentLoaded", function () {
  var antSearchInput = document.getElementById("antSearchInput");
  var antTable = document.getElementById("antTable");
  var antTableBody = document.getElementById("antTableBody");
  var noSpeciesFoundWarning = document.getElementById("noSpeciesFoundWarning");

  antSearchInput.addEventListener("keyup", function () {
    var searchText = this.value.toLowerCase();
    var visibleElements = 0;
    var rows = antTableBody.children;

    for (var i = 0; i < rows.length; i++) {
      var row = rows[i];
      var text = row.textContent.toLowerCase();
      var found = text.indexOf(searchText) > -1;
      row.style.display = found ? "" : "none";
      if (found) {
        visibleElements++;
      }
    }

    noSpeciesFoundWarning.style.display = visibleElements === 0 ? "" : "none";
    antTable.style.display = visibleElements > 0 ? "" : "none";
  });
});
