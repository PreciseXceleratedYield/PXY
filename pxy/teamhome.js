'use strict';

const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');

const MAX_POSTS = 500;
const MAX_AUTHOR_LENGTH = 40;
const MAX_BODY_LENGTH = 2000;
const MIN_PASSWORD_BYTES = 16;

function getPostsPath() {
    if (process.env.TEAM_HOME_DATA_FILE) {
        return path.resolve(process.env.TEAM_HOME_DATA_FILE);
    }
    const home = process.env.PXY_HOME || os.homedir();
    return path.join(home, '.pxy', 'team-home-posts.json');
}

function isPasswordConfigured(password) {
    return typeof password === 'string'
        && Buffer.byteLength(password, 'utf8') >= MIN_PASSWORD_BYTES;
}

function passwordMatches(supplied, expected) {
    if (typeof supplied !== 'string' || !isPasswordConfigured(expected)) {
        return false;
    }
    const suppliedBuffer = Buffer.from(supplied, 'utf8');
    const expectedBuffer = Buffer.from(expected, 'utf8');
    return suppliedBuffer.length === expectedBuffer.length
        && crypto.timingSafeEqual(suppliedBuffer, expectedBuffer);
}

function readPosts(filePath = getPostsPath()) {
    let source;
    try {
        source = fs.readFileSync(filePath, 'utf8');
    } catch (error) {
        if (error.code === 'ENOENT') {
            return [];
        }
        throw error;
    }

    const posts = JSON.parse(source);
    if (!Array.isArray(posts) || posts.some((post) => (
        !post
        || typeof post.id !== 'string'
        || typeof post.author !== 'string'
        || typeof post.body !== 'string'
        || typeof post.createdAt !== 'string'
    ))) {
        throw new Error('Stored family posts have an invalid format.');
    }
    return posts;
}

function writePosts(posts, filePath) {
    const directory = path.dirname(filePath);
    fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
    const temporaryPath = `${filePath}.${process.pid}.${crypto.randomBytes(8).toString('hex')}.tmp`;
    try {
        fs.writeFileSync(temporaryPath, JSON.stringify(posts, null, 2), {
            encoding: 'utf8',
            flag: 'wx',
            mode: 0o600,
        });
        fs.renameSync(temporaryPath, filePath);
    } catch (error) {
        try {
            fs.unlinkSync(temporaryPath);
        } catch (cleanupError) {
            if (cleanupError.code !== 'ENOENT') {
                console.error('[TEAM@HOME] Could not clean temporary post file:', cleanupError.message);
            }
        }
        throw error;
    }
}

function addPost({ author, body }, filePath = getPostsPath()) {
    const normalizedAuthor = typeof author === 'string' ? author.trim() : '';
    const normalizedBody = typeof body === 'string' ? body.trim() : '';
    if (!normalizedAuthor || normalizedAuthor.length > MAX_AUTHOR_LENGTH) {
        throw new RangeError(`author must be between 1 and ${MAX_AUTHOR_LENGTH} characters.`);
    }
    if (!normalizedBody || normalizedBody.length > MAX_BODY_LENGTH) {
        throw new RangeError(`body must be between 1 and ${MAX_BODY_LENGTH} characters.`);
    }

    const post = {
        id: crypto.randomUUID(),
        author: normalizedAuthor,
        body: normalizedBody,
        createdAt: new Date().toISOString(),
    };
    const posts = [post, ...readPosts(filePath)].slice(0, MAX_POSTS);
    writePosts(posts, filePath);
    return post;
}

module.exports = {
    MAX_AUTHOR_LENGTH,
    MAX_BODY_LENGTH,
    MAX_POSTS,
    addPost,
    getPostsPath,
    isPasswordConfigured,
    passwordMatches,
    readPosts,
};
