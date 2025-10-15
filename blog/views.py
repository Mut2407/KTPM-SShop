from django.shortcuts import render, get_object_or_404
from django.shortcuts import render
from .models import Post

def blog_list(request):
    posts = Post.objects.order_by('-created_at')
    return render(request, 'blog/blog.html', {'posts': posts})

def blog_details(request, slug):
    post = get_object_or_404(Post, slug=slug)
    return render(request, 'blog/blog_details.html', {'post': post})
