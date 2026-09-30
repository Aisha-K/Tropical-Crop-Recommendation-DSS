X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)


model.fit(X_train, y_train)
predictions = model.predict(X_test)


#final model
joblib.dump(model, "../models/crop_model.pkl")