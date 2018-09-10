var socialWallHelper = {

  init: function() {
      $(window).bind('scroll', loadOnScroll);
      $('#modal-body').on('click', '#btn-post-cancel', function() {
        $('#dialog-form-post').modal('toggle');
      })
      $.ajaxSetup({
        beforeSend: function(xhr, settings) {
          if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", $.cookie('csrftoken'))
          }
        }
      })
      // Init post masonry
      var $grid = $('.grid').masonry({
        itemSelector: '.grid-item',
        columWidth: '.grid-sizer',
        percentPosition: true,
      });
      this.initNewPostBtn();

  },
  initNewPostBtn: function() {
    // -------------------- create post start --------------------
    $('.row').on('click', '#btn-newpost', function() {
      var form = $('#form-post')
      var url = $(this).attr('action')

      $.ajax({
        type: 'get',
        url: url,
        success: function (data) {
          console.log(data['form'])
          $('.modal-body').html(data['form'])
          $('#btn-post-create').show()
          $('#btn-post-update').hide()
          $('#dialog-form-post').modal('show')
        }
      })
    })

    $('form').submit(function (e) {

      e.preventDefault();

      url = $(this).attr('action');

      data = $(this).formcontrol().data();
      hasFile = false;

      try {
        $('#id_file')[0].files[0].name;
        form = new FormData();
        $.each(data, function(key, val) {
          form.append(key, val);
        });
        form.append('file', $('#id_file')[0].files[0])
        hasFile = true;
      } catch (e) {

      }

      if(hasFile) {
        console.log('has file')
        $.ajax({
          type: 'post',
          url: url,
          data: form,
          contentType: false,
          processData: false,
          success: function(data) {
            console.log(data)
          }
        })
      } else {
        console.log('no file')
        $.ajax({
          type: 'post',
          url: url,
          data: data,
          success: function(data) {
            console.log(data)
          }
        })
      }
    })
    // -------------------- create post end --------------------

  },
  initPost: function($posts){
    // -------------------- edit post start --------------------
    $posts.find('.post-edit').click(function () {
      var id = $(this).attr('id')
      // alert(id)
      $.ajax({
        type: 'get',
        url: '{% url "posts:api_post_UD" 0  %}'.replace('0', id),
        success: function(data) {
          var title = data['title']
          var content = data['content']
          var file = data['file']
          // alert(title)
          // alert(content)
          $('#id_title').val(title)
          CKEDITOR.instances['id_content'].setData(content)
          // $('#id_file')
          // if(file != null) {
          // 	console.log('has file')
          // 	$('#id_file')[0].files[0] = file
          // 	console.log($('#id_file')[0].files[0])
          // }
          $('#id_file').val('')
          $('#btn-post-update').show()
          $('#btn-post-create').hide()
          $('#dialog-form-post').modal('show')
        }
      })
    })

    $('#btn-post-update').click(function () {
      //
      $.ajax({
        type: 'patch',
        url: '{% url "posts:api_post_C" %}' + id,
        success: function () {

        }
      })
    })
    // -------------------- edit post end --------------------


    // -------------------- delete post start --------------------

    $('.post-delete').on('click', function () {
      var id = $(this).attr('id')
      $.ajax({
        type: 'DELETE',
        url: '{% url "posts:api_post_C" %}' + id,
        success: function() {
          $('#span-' + id).slideUp(200)
          $('#div-' + id).slideUp(200)
        }
      })
    })
    // -------------------- delete post end --------------------


    // -------------------- edit comment start --------------------
    $('.edit-comment').on('click', function () {
      // alert($(this).attr('id'))
      var id = $(this).attr('id')
      $('#modal-comment').modal('toggle')
      $('#text-edit-comment').val('test')
      $('#text-edit-comment').focus()
    })
    // -------------------- edit comment end --------------------


    // -------------------- reply start --------------------
    $('.post-reply').on('click', function () {
      var id = $(this).attr('id')
      // alert(id)
      $('#reply-' + id).after('')
    })
    // -------------------- reply end --------------------


    // -------------------- reply text start --------------------
    // $('.socialwall-reply-text').bind('enterKey', function () {
    // 	alert('test')
    // })
    $('.socialwall-reply-text').keyup(function (e) {
      if(e.keyCode == 13) {
        var id = $(this).attr('id').split('-')[1]
        var text = $(this).val()
        // alert(id)
        $.ajax({
          type: 'post',
          url: '/comments/api/',
          data: {
            csrfmiddlewaretoken: '{{ csrf_token }}',
            'object_id': id,
            'content': text,
          },
          success: function(data) {
            $('#insert-reply-' + id).before(data)
            $('#reply-' + id).val('')
            // alert(data['user'] + '   ' + data['content_type'] + '   ' + data['object_id'] + '   ' + data['content'])
            //
          }
        })
      }
    })
    // -------------------- reply text end --------------------

    // -------------------- Read More Start --------------------
    $('.read-more').readMore()

    $('#row-post').on('click', 'button', function () {
      $grid.masonry('layout')
      console.log('read more ok, reloaditems ok')
    })
    // -------------------- Read More End --------------------

  }
}

// var initPost = function($posts) {
//
// }

// -------------------- like thumb start --------------------
// $('.toggle-like').on('click', '.reply-like', function() {
//   $(this).children('i').removeClass('fa-thumbs-o-up')
//   $(this).children('i').addClass('fa-thumbs-up')
//   $(this).removeClass('reply-like')
//   $(this).addClass('reply-like-up')
// })
//
// $('.toggle-like').on('click', '.reply-like-up', function() {
//   $(this).children('i').removeClass('fa-thumbs-up')
//   $(this).children('i').addClass('fa-thumbs-o-up')
//   $(this).removeClass('reply-like-up')
//   $(this).addClass('reply-like')
// })
// -------------------- like thumb start --------------------


// // -------------------- hide post start --------------------
// $('.post-hide').on('click', function () {
//   var id = $(this).attr('id')
//   $('#post-area-' + id).remove()
//   // $grid.masonry('layout')
//   $grid.masonry('destroy')
//   $grid.masonry()
//   console.log('hide post ok')
// })
// // -------------------- hide post end --------------------


// ---------- Infinite Scroll Satrt ----------
var pageNum = 1
var hasNextPage = true

var loadOnScroll = function() {
  if( (($(document).height() - $(window).scrollTop()) / 2) <  $(window).height()){
    $(window).unbind('scroll', loadOnScroll)
    loadItem()
  }
}

var loadItem = function() {
  if (hasNextPage == false) {
    return false
  }
  console.log($(window).scrollTop())
  console.log($(document).height())
  console.log($(window).height())

  pageNum = pageNum + 1
  $.ajax({
    url: '/posts/next/' + pageNum,
    success: function(data) {
      hasNextPage = true
      var $item = $(data)

      $grid.append($item);

      $item.find('.read-more').readMore();
      $grid.masonry('appended', $item);

    },
    error: function(data) {
      hasNextPage = false
    },
    complete: function(data) {
      $(window).bind('scroll', loadOnScroll)
    }
  })
}
// ---------- Infinite Scroll end ----------


// solve the problem ckeditor with modal can't focus on ckeditor's modal like insert img
$.fn.modal.Constructor.prototype.enforceFocus = function () {
var $modalElement = this.$element;
$(document).on('focusin.modal',
    function (e) {
        var $parent = $(e.target.parentNode);
        if ($modalElement[0] !== e.target &&
            !$modalElement.has(e.target).length &&
            !$parent.hasClass('cke_dialog_ui_input_select') &&
            !$parent.hasClass('cke_dialog_ui_input_text')) {
            $modalElement.focus();
        }
    });
};