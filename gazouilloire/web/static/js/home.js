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
        console.log(vals)
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
    if (ns.table) {
      $('#preview').hide();
      ns.table.destroy();
      $('#preview table').empty();
    }
    d3.csv(dataUrl, function(d){
      return d;
    }, function(data){
      $('#loader').hide();
      $('#submit').attr("disabled", null);
      if (!data.length) return;
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
    $('.bootstrap-tagsinput').addClass('col-md-8 col-xs-8')
    $('form').on('change', function(d){console.log("WOUP", d)});
  });
})(window.gazouilloire = window.gazouilloire || {});
