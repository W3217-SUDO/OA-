$(document).ready(function () {
    var officer = new AssociateAvailableUserForTask(
          $("#div_officerlist"),
          $("#Task_Officer_Input"),
          $("#Task_Officer_Input"),
           task.Tasks.Task.Officer.AddIn
      );
    var associates = new AssociateAvailableUserForTask(
        $("#div_associateslist"),
        $("#Task_Associates_Input"),
        $("#Task_Associates_Input"),
         task.Tasks.Task.Associates.AddIn
    );
});