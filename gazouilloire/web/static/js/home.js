(function(ns){
  ns.addDatePicker = function(id){
    $('#'+id).datepicker({format: 'yyyy-mm-dd'})
    .on('changeDate', function(e){console.log(e)});
  };
  ns.addTagSelect = function(id, initVals){
    var input = $('#'+id),
      hid = $('input[name='+id+']'),
      getHid = function(){ return hid.val().split(/\|/)},
      formatHid = function(vals){
        hid.val(vals.filter(function(v){ return v }).join('|'));
      };
    input.tagsinput();
    initVals.split(/\|/).forEach(function(val){
      input.tagsinput('add', val);
    });
    $(input).on('itemAdded', function(e){
      var values = getHid();
      values.push(e.item);
      formatHid(values);
    }).on('itemRemoved', function(e){
      formatHid(getHid().filter(function(v){ return v !== e.item }))
    });
  };
  ns.submit = function(){
    var dataUrl = $("form").attr("action") + "?" + $("form").serialize();
    $('#loader').show();
    $('#submit').attr("disabled", "disabled");
    $('#errors').hide();
    $('#errors ul').empty();
    $('#nomatch').hide();
    if (ns.table) {
      $('#preview').hide();
      ns.table.destroy();
      $('#preview table').empty();
    }
    d3.csv(dataUrl, function(d){
      return d;
    }, function(error, data){
      $('#loader').hide();
      $('#submit').attr("disabled", null);
      if (error)
        return console.log(data, error);
      if (data.columns[0] === "error") {
        $('#errors').show();
        return d3.select('#errors ul')
          .selectAll('li')
          .data(data).enter()
          .append('li')
          .text(function(d){ return d.error});
      }
      if (!data.length)
        return $('#nomatch').show();
      $('#preview').show();
      ns.table = $('#preview table').DataTable({
        data: data,
        columns: [
          { data: 'id' },
          { data: 'from_user_name' },
          { data: 'text' },
          { data: 'created_at' }
        ]
      });
    });
  };
  ns.download = function(){
    $('form').submit();
  };
  $(document).ready(function(){
    ns.addDatePicker('startdate');
    ns.addDatePicker('enddate');
    ns.addTagSelect('query', $('#query_val').val());
    ns.addTagSelect('filters', $('#filters_val').val());
    $('#submit').on('click', ns.submit);
    $('#download').on('click', ns.download);
    $('#selected').on('change', function(d){
      $("#selected_val").val(d.currentTarget.checked ? "checked" : "");
    });
    $('.bootstrap-tagsinput').addClass('col-md-8 col-xs-8')
  });
})(window.gazouilloire = window.gazouilloire || {});
