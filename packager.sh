pyinstaller cb_release_note.spec  --clean


mkdir ./package
cp ./dist/cb-release-note ./package
cp ./cb_release_notes_config.yaml ./package
cp ./cb_release_config_schema.yaml ./package

# Don't pack the password file.
# cp ./.passwords.yaml ./package

cp -r ./templates ./package
cd package || exit
zip -r  ../package.zip .
cd ..




