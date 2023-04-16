from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'mysite/static/uploads'
db = SQLAlchemy(app)

class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(20), nullable=False)
    photos = db.relationship('Photo', backref='post', lazy=True)
    comments = db.relationship('Comment', back_populates='post', cascade='all, delete')
    uuid = db.Column(db.String(36), nullable=False)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    post = db.relationship('Post', back_populates='comments')  # Add this line

@app.route('/')
def index():
    search = request.args.get('search', '')
    category = request.args.get('category', 'All')
    if category == 'All':
        posts = Post.query.filter(Post.title.contains(search) | Post.description.contains(search))
    else:
        posts = Post.query.filter(Post.category == category,
                                   Post.title.contains(search) | Post.description.contains(search))

    return render_template('index.html', posts=posts)

@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def post(post_id):
    post = Post.query.get_or_404(post_id)
    if request.method == 'POST':
        comment_content = request.form['content']
        new_comment = Comment(content=comment_content, post_id=post.id)
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('post', post_id=post.id))

    return render_template('post.html', post=post)

@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    if request.method == 'POST':
        user_uuid = session.get('uuid')
        if not user_uuid:
            user_uuid = str(uuid.uuid4())
            session['uuid'] = user_uuid

        title = request.form['title']
        description = request.form['description']
        price = request.form['price']
        category = request.form['category']

        filenames = []
        for i in range(1, 5):
            photo = request.files.get(f'photo{i}')
            if photo and photo.filename:
                filename = secure_filename(photo.filename)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                filenames.append(filename)

        if not filenames:
            print("Error: no photos uploaded")
            return redirect(url_for('create_post'))

        new_post = Post(title=title, description=description, price=price, category=category, uuid=user_uuid)
        db.session.add(new_post)
        db.session.flush()

        for filename in filenames:
            new_photo = Photo(filename=filename, post_id=new_post.id)
            db.session.add(new_photo)

        db.session.commit()
        return redirect(url_for('index'))

    return render_template('create_post.html')

@app.route('/post/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if session.get('uuid') != post.uuid:
        flash('You are not authorized to delete this post.', 'error')
        return redirect(url_for('post', post_id=post.id))
    else:
        for photo in post.photos:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], photo.filename))
            db.session.delete(photo)

        db.session.delete(post)
        db.session.commit()
        flash('Your post has been deleted.', 'success')
        return redirect(url_for('index'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=1234)

