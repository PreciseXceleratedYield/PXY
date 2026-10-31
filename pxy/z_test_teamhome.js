'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const {
    MAX_POSTS,
    addPost,
    isPasswordConfigured,
    passwordMatches,
    readPosts,
} = require('./teamhome');

test('test-machine family password is 1 and compares safely', () => {
    assert.equal(isPasswordConfigured(''), false);
    assert.equal(isPasswordConfigured('1'), true);
    assert.equal(passwordMatches('1', '1'), true);
    assert.equal(passwordMatches('wrong', '1'), false);
    assert.equal(passwordMatches(null, '1'), false);
});

test('posts persist, trim input, and reject oversized content', (t) => {
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'team-home-test-'));
    const filePath = path.join(directory, 'posts.json');
    t.after(() => fs.rmSync(directory, { recursive: true, force: true }));

    assert.deepEqual(readPosts(filePath), []);
    const post = addPost({ author: '  Alex  ', body: '  Hello family!  ' }, filePath);
    assert.equal(post.author, 'Alex');
    assert.equal(post.body, 'Hello family!');
    assert.deepEqual(readPosts(filePath), [post]);
    assert.throws(() => addPost({ author: 'A', body: '  ' }, filePath), RangeError);
});

test('post history is capped at the newest 500 posts', (t) => {
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'team-home-test-'));
    const filePath = path.join(directory, 'posts.json');
    t.after(() => fs.rmSync(directory, { recursive: true, force: true }));

    for (let index = 0; index <= MAX_POSTS; index += 1) {
        addPost({ author: 'Family', body: `Post ${index}` }, filePath);
    }
    const posts = readPosts(filePath);
    assert.equal(posts.length, MAX_POSTS);
    assert.equal(posts[0].body, `Post ${MAX_POSTS}`);
    assert.equal(posts.at(-1).body, 'Post 1');
});
