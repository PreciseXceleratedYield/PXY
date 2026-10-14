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

test('family password requires a long value and compares safely', () => {
    assert.equal(isPasswordConfigured('short'), false);
    assert.equal(isPasswordConfigured('family-password-2026'), true);
    assert.equal(passwordMatches('family-password-2026', 'family-password-2026'), true);
    assert.equal(passwordMatches('wrong-password', 'family-password-2026'), false);
    assert.equal(passwordMatches(null, 'family-password-2026'), false);
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
